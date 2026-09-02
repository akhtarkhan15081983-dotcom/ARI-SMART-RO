from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User

from .models import Branch, Company, CompanyLifecycleEvent, CompanyMembership, CompanySubscription, SubscriptionPlan
from .serializers import (
    CompanyLifecycleEventSerializer, CompanySerializer, MembershipSerializer,
    PublicCompanyBrandSerializer, SubscriptionPlanSerializer,
)


def _platform_super_admin(user):
    return bool(user and user.is_authenticated and user.is_active and user.is_superuser)


class PlatformSuperAdminMixin:
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not _platform_super_admin(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Platform super-admin access is required.")


class PublicPlanListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True, is_public=True)
        return Response({"success": True, "plans": SubscriptionPlanSerializer(plans, many=True).data})


class PublicCompanyBrandAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            company = Company.objects.select_related("subscription").get(
                slug=slug, is_active=True, lifecycle_status="ACTIVE"
            )
        except Company.DoesNotExist:
            return Response({"success": False, "message": "Company workspace not found."}, status=404)
        subscription = getattr(company, "subscription", None)
        if subscription is None or not subscription.has_access:
            return Response({"success": False, "message": "Company workspace is currently unavailable."}, status=403)
        return Response({
            "success": True,
            "brand": PublicCompanyBrandSerializer(company, context={"request": request}).data,
        })


class MyCompaniesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = CompanyMembership.objects.filter(
            user=request.user, is_active=True, company__is_active=True,
        ).select_related("company", "branch", "company__subscription__plan")
        return Response({"success": True, "memberships": MembershipSerializer(memberships, many=True).data})


class CompanyCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        if request.user.role not in {"ADMIN", "MANAGER"}:
            return Response({"success": False, "message": "Only an authorised business owner can create a company."}, status=403)
        serializer = CompanySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        branch = Branch.objects.create(
            company=company,
            name="Head Office",
            code="HO",
            phone=company.phone,
            address=company.address,
            city=company.city,
            state=company.state,
            pincode=company.pincode,
            is_head_office=True,
        )
        CompanyMembership.objects.create(company=company, user=request.user, role="OWNER", branch=branch)
        plan = SubscriptionPlan.objects.filter(code="starter", is_active=True).first()
        if plan:
            now = timezone.now()
            CompanySubscription.objects.create(
                company=company,
                plan=plan,
                status="TRIAL",
                starts_at=now,
                current_period_end=now + timedelta(days=14),
                trial_ends_at=now + timedelta(days=14),
            )
        return Response({"success": True, "company": CompanySerializer(company, context={"request": request}).data}, status=status.HTTP_201_CREATED)


class SuperAdminDashboardAPIView(PlatformSuperAdminMixin, APIView):
    def get(self, request):
        now = timezone.now()
        companies = Company.objects.annotate(
            branch_count=Count("branches", filter=Q(branches__is_active=True), distinct=True),
            member_count=Count("memberships", filter=Q(memberships__is_active=True), distinct=True),
        ).select_related("subscription__plan").order_by("-created_at")
        subscriptions = CompanySubscription.objects.select_related("plan", "company")
        active = subscriptions.filter(status="ACTIVE", current_period_end__gt=now)
        trials = subscriptions.filter(status="TRIAL", current_period_end__gt=now)
        recurring = active.filter(plan__billing_interval="MONTHLY").aggregate(total=Sum("plan__price"))["total"] or 0
        annual = active.filter(plan__billing_interval="ANNUAL").aggregate(total=Sum("plan__price"))["total"] or 0
        recurring += annual / 12
        company_rows = []
        for company in companies:
            subscription = getattr(company, "subscription", None)
            company_rows.append({
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
                "phone": company.phone,
                "city": company.city,
                "is_active": company.is_active,
                "lifecycle_status": company.lifecycle_status,
                "lifecycle_reason": company.lifecycle_reason,
                "archived_at": company.archived_at,
                "deletion_scheduled_for": company.deletion_scheduled_for,
                "branches": company.branch_count,
                "members": company.member_count,
                "plan": subscription.plan.name if subscription else "No plan",
                "plan_code": subscription.plan.code if subscription else "",
                "subscription_status": subscription.status if subscription else "NONE",
                "current_period_end": subscription.current_period_end if subscription else None,
                "has_access": subscription.has_access if subscription else False,
            })
        plan_distribution = list(
            subscriptions.values("plan__name").annotate(companies=Count("id")).order_by("plan__sort_order")
        )
        return Response({
            "success": True,
            "metrics": {
                "total_companies": companies.count(),
                "active_companies": companies.filter(is_active=True).count(),
                "active_subscriptions": active.count(),
                "trials": trials.count(),
                "past_due": subscriptions.filter(status="PAST_DUE").count(),
                "monthly_recurring_revenue": f"{recurring:.2f}",
            },
            "plan_distribution": plan_distribution,
            "companies": company_rows,
        })


class SuperAdminSubscriptionStatusAPIView(PlatformSuperAdminMixin, APIView):
    def post(self, request, company_id):
        allowed = {choice[0] for choice in CompanySubscription.STATUS_CHOICES}
        next_status = str(request.data.get("status", "")).upper()
        if next_status not in allowed:
            return Response({"success": False, "message": "Invalid subscription status."}, status=400)
        try:
            subscription = CompanySubscription.objects.select_related("company", "plan").get(company_id=company_id)
        except CompanySubscription.DoesNotExist:
            return Response({"success": False, "message": "Company subscription not found."}, status=404)
        subscription.status = next_status
        subscription.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "company_id": company_id, "status": subscription.status})


class SuperAdminCompanyLifecycleAPIView(PlatformSuperAdminMixin, APIView):
    ACTION_STATUS = {
        "SUSPEND": "SUSPENDED", "DEACTIVATE": "DEACTIVATED",
        "ARCHIVE": "ARCHIVED", "RESTORE": "ACTIVE",
        "REQUEST_DELETION": "PENDING_DELETION", "CANCEL_DELETION": "ARCHIVED",
    }

    @transaction.atomic
    def post(self, request, company_id):
        try:
            company = Company.objects.select_for_update().get(pk=company_id)
        except Company.DoesNotExist:
            return Response({"success": False, "message": "Company not found."}, status=404)
        action = str(request.data.get("action", "")).upper()
        reason = str(request.data.get("reason", "")).strip()
        if action not in self.ACTION_STATUS:
            return Response({"success": False, "message": "Invalid lifecycle action."}, status=400)
        if len(reason) < 5:
            return Response({"success": False, "message": "Please provide a clear reason (minimum 5 characters)."}, status=400)
        if action == "REQUEST_DELETION" and company.lifecycle_status != "ARCHIVED":
            return Response({"success": False, "message": "Archive the company before requesting permanent deletion."}, status=409)
        if action == "CANCEL_DELETION" and company.lifecycle_status != "PENDING_DELETION":
            return Response({"success": False, "message": "This company has no pending deletion request."}, status=409)

        previous = company.lifecycle_status
        next_status = self.ACTION_STATUS[action]
        now = timezone.now()
        company.lifecycle_status = next_status
        company.lifecycle_reason = reason
        company.is_active = next_status == "ACTIVE"
        if action == "ARCHIVE":
            company.archived_at = now
        elif action == "RESTORE":
            company.archived_at = None
            company.deletion_scheduled_for = None
        if action == "REQUEST_DELETION":
            company.deletion_scheduled_for = now + timedelta(days=30)
        elif action == "CANCEL_DELETION":
            company.deletion_scheduled_for = None
        company.save()
        CompanyLifecycleEvent.objects.create(
            company=company, company_name=company.name, company_slug=company.slug,
            action=action, previous_status=previous, new_status=next_status,
            reason=reason, actor=request.user,
        )
        return Response({
            "success": True, "message": f"Company lifecycle updated to {next_status}.",
            "company": CompanySerializer(company, context={"request": request}).data,
        })

    @transaction.atomic
    def delete(self, request, company_id):
        try:
            company = Company.objects.select_for_update().get(pk=company_id)
        except Company.DoesNotExist:
            return Response({"success": False, "message": "Company not found."}, status=404)
        confirmation = str(request.data.get("confirmation", "")).strip()
        reason = str(request.data.get("reason", "")).strip()
        if company.lifecycle_status != "PENDING_DELETION":
            return Response({"success": False, "message": "A deletion request is required first."}, status=409)
        if not company.deletion_scheduled_for or company.deletion_scheduled_for > timezone.now():
            return Response({"success": False, "message": "The 30-day deletion grace period has not finished."}, status=409)
        if confirmation != company.slug:
            return Response({"success": False, "message": "Type the exact company slug to confirm deletion."}, status=400)
        if len(reason) < 10:
            return Response({"success": False, "message": "A detailed deletion reason is required."}, status=400)
        subscription = getattr(company, "subscription", None)
        if subscription and subscription.status in {"ACTIVE", "TRIAL", "PAST_DUE"}:
            return Response({"success": False, "message": "Cancel the subscription before permanent deletion."}, status=409)
        CompanyLifecycleEvent.objects.create(
            company=company, company_name=company.name, company_slug=company.slug,
            action="PURGE", previous_status=company.lifecycle_status, new_status="DELETED",
            reason=reason, actor=request.user,
            metadata={"branches": company.branches.count(), "memberships": company.memberships.count()},
        )
        company.delete()
        return Response({"success": True, "message": "Company data was permanently deleted."})


class SuperAdminCompanyLifecycleHistoryAPIView(PlatformSuperAdminMixin, APIView):
    def get(self, request, company_id):
        events = CompanyLifecycleEvent.objects.filter(company_id=company_id)[:100]
        return Response({
            "success": True,
            "events": CompanyLifecycleEventSerializer(events, many=True).data,
        })


class SuperAdminCompanyDetailAPIView(PlatformSuperAdminMixin, APIView):
    EDITABLE_FIELDS = {
        "name", "legal_name", "phone", "email", "gstin", "primary_color",
        "secondary_color", "support_phone", "support_email", "app_display_name",
        "tagline", "welcome_message", "show_public_shop", "enabled_modules",
        "address", "city", "state", "pincode", "timezone",
    }

    def get(self, request, company_id):
        try:
            company = Company.objects.select_related("subscription__plan").get(pk=company_id)
        except Company.DoesNotExist:
            return Response({"success": False, "message": "Company not found."}, status=404)
        return Response({
            "success": True,
            "company": CompanySerializer(company, context={"request": request}).data,
        })

    @transaction.atomic
    def patch(self, request, company_id):
        try:
            company = Company.objects.select_for_update().get(pk=company_id)
        except Company.DoesNotExist:
            return Response({"success": False, "message": "Company not found."}, status=404)
        payload = {key: value for key, value in request.data.items() if key in self.EDITABLE_FIELDS}
        if not payload:
            return Response({"success": False, "message": "No editable company fields supplied."}, status=400)
        serializer = CompanySerializer(company, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        CompanyLifecycleEvent.objects.create(
            company=company, company_name=company.name, company_slug=company.slug,
            action="UPDATE_PROFILE", previous_status=company.lifecycle_status,
            new_status=company.lifecycle_status, reason="Company profile and branding updated.",
            actor=request.user, metadata={"updated_fields": sorted(payload.keys())},
        )
        return Response({
            "success": True, "message": "Company details updated successfully.",
            "company": CompanySerializer(company, context={"request": request}).data,
        })


class SuperAdminCompanyOnboardingAPIView(PlatformSuperAdminMixin, APIView):
    @transaction.atomic
    def post(self, request):
        company_payload = {
            key: request.data.get(key, "")
            for key in [
                "name", "legal_name", "slug", "phone", "email", "gstin",
                "primary_color", "secondary_color", "support_phone",
                "support_email", "app_display_name", "tagline", "welcome_message",
                "show_public_shop", "enabled_modules", "address", "city", "state", "pincode", "timezone",
            ]
            if request.data.get(key) not in (None, "")
        }
        serializer = CompanySerializer(data=company_payload)
        serializer.is_valid(raise_exception=True)

        owner_phone = str(request.data.get("owner_phone", "")).strip()
        owner_name = str(request.data.get("owner_name", "")).strip()
        initial_password = str(request.data.get("initial_password", ""))
        plan_code = str(request.data.get("plan_code", "starter")).strip().lower()
        if len(owner_phone) != 10 or not owner_phone.isdigit():
            return Response({"success": False, "message": "Owner phone must be a valid 10-digit number."}, status=400)
        if not owner_name:
            return Response({"success": False, "message": "Owner name is required."}, status=400)
        try:
            validate_password(initial_password)
        except DjangoValidationError as exc:
            return Response({"success": False, "message": " ".join(exc.messages)}, status=400)
        try:
            plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({"success": False, "message": "Selected subscription plan is unavailable."}, status=400)

        existing_owner = User.objects.filter(phone=owner_phone).first()
        if existing_owner and existing_owner.role == "CUSTOMER":
            return Response({"success": False, "message": "This phone already belongs to a customer account."}, status=400)
        if existing_owner and CompanyMembership.objects.filter(user=existing_owner, is_active=True).exists():
            return Response({"success": False, "message": "This owner already belongs to an active company."}, status=400)

        company = serializer.save()
        branch = Branch.objects.create(
            company=company,
            name="Head Office",
            code="HO",
            phone=company.phone,
            address=company.address,
            city=company.city,
            state=company.state,
            pincode=company.pincode,
            is_head_office=True,
        )
        first_name, _, last_name = owner_name.partition(" ")
        if existing_owner:
            owner = existing_owner
            owner.first_name = first_name
            owner.last_name = last_name
            owner.role = "ADMIN"
            owner.is_active = True
            owner.is_verified = True
            owner.set_password(initial_password)
            owner.save()
        else:
            owner = User.objects.create_user(
                phone=owner_phone,
                password=initial_password,
                first_name=first_name,
                last_name=last_name,
                role="ADMIN",
                is_active=True,
                is_verified=True,
            )
        CompanyMembership.objects.create(company=company, user=owner, role="OWNER", branch=branch)
        now = timezone.now()
        subscription = CompanySubscription.objects.create(
            company=company,
            plan=plan,
            status="TRIAL",
            starts_at=now,
            current_period_end=now + timedelta(days=14),
            trial_ends_at=now + timedelta(days=14),
        )
        return Response(
            {
                "success": True,
                "message": "Company, owner, head office and trial subscription created successfully.",
                "company": CompanySerializer(company, context={"request": request}).data,
                "owner": {"id": owner.id, "name": owner.get_full_name(), "phone": owner.phone},
                "subscription": {"plan": plan.name, "status": subscription.status, "trial_ends_at": subscription.trial_ends_at},
            },
            status=status.HTTP_201_CREATED,
        )