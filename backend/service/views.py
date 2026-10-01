from io import BytesIO

import openpyxl
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin, IsOperationsUser, IsStaffOperator, STAFF_ROLES, user_role
from assets.models import ROAsset
from customers.models import Customer
from partmaster.models import PartMaster
from products.models import ROModel
from tenancy.models import CompanyMembership
from .models import Service, ServiceIntervalPolicy
from .serializers import ServiceSerializer
from .smart_care import asset_health, record_completed_service_cycles


def _linked_customer_for(user):
    """Resolve exactly one customer record for a verified customer account.

    Shared/duplicate phone numbers are valid ARI business data, so phone alone
    must never grant access to every record with that number. Prefer the durable
    user link; legacy records can claim only the first deterministic unlinked row.
    """
    if user_role(user) != "CUSTOMER" or not user.is_verified or not user.is_active:
        return None

    linked = Customer.objects.filter(user=user, is_active=True).first()
    if linked is not None:
        return linked

    legacy = (
        Customer.objects.filter(
            phone=user.phone,
            user__isnull=True,
            is_active=True,
        )
        .order_by("id")
        .first()
    )
    if legacy is not None:
        legacy.user = user
        legacy.save(update_fields=["user"])
    return legacy


def _active_company_for(user):
    membership = (
        CompanyMembership.objects.filter(
            user=user,
            is_active=True,
            company__is_active=True,
            company__lifecycle_status="ACTIVE",
        )
        .select_related("company")
        .first()
    )
    return membership.company if membership else None


def _service_queryset_for(user, include_customer=True):
    queryset = Service.objects.select_related(
        "customer",
        "engineer",
        "engineer__user",
        "ro_asset",
    )
    role = user_role(user)

    if role in STAFF_ROLES:
        company = _active_company_for(user)
        return queryset.filter(company=company) if company is not None else queryset.none()
    if role == "ENGINEER":
        return queryset.filter(engineer__user=user)
    if include_customer and role == "CUSTOMER":
        customer = _linked_customer_for(user)
        return queryset.filter(customer=customer) if customer is not None else queryset.none()
    return queryset.none()


class ServiceListAPIView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _service_queryset_for(self.request.user).order_by("-id")


class ServiceCreateAPIView(generics.CreateAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsStaffOperator]


class ServiceDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _service_queryset_for(self.request.user)


class ServiceUpdateAPIView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsOperationsUser]

    def get_queryset(self):
        return _service_queryset_for(self.request.user, include_customer=False)


class CompleteServiceAPIView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsOperationsUser]

    def get_queryset(self):
        return _service_queryset_for(self.request.user, include_customer=False)

    @transaction.atomic
    def _complete(self):
        service = get_object_or_404(
            self.get_queryset().select_for_update(), pk=self.kwargs["pk"]
        )
        self.check_object_permissions(self.request, service)
        if service.status == "COMPLETED":
            record_completed_service_cycles(service)
            return Response({
                "success": True,
                "service_id": service.service_id,
                "message": "Service completed successfully.",
            }, status=status.HTTP_200_OK)
        service.status = "COMPLETED"
        service.completed_date = timezone.now()
        service.save(update_fields=["status", "completed_date", "updated_at"])
        record_completed_service_cycles(service)
        return Response(
            {
                "success": True,
                "service_id": service.service_id,
                "message": "Service completed successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        return self._complete()

    def update(self, request, *args, **kwargs):
        return self._complete()


class ROHealthAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id):
        role = user_role(request.user)
        configuration_key = request.GET.get("configuration", "").strip()

        if role == "CUSTOMER":
            customer = _linked_customer_for(request.user)
            if customer is None or customer.company_id is None:
                return Response({"detail": "Customer workspace not found."}, status=404)
            asset = get_object_or_404(
                ROAsset.objects.select_related("ro_model", "current_customer"),
                asset_id=asset_id,
                current_customer=customer,
                is_active=True,
            )
            company = customer.company
        elif role in STAFF_ROLES:
            company = _active_company_for(request.user)
            if company is None:
                return Response({"detail": "Active company workspace not found."}, status=403)
            asset = get_object_or_404(
                ROAsset.objects.select_related("ro_model", "current_customer"),
                asset_id=asset_id,
                current_customer__company=company,
                is_active=True,
            )
        elif role == "ENGINEER":
            service = (
                Service.objects.filter(
                    engineer__user=request.user,
                    ro_asset__asset_id=asset_id,
                )
                .select_related("company", "customer__company", "ro_asset__ro_model")
                .order_by("-id")
                .first()
            )
            if service is None:
                return Response({"detail": "RO asset is not available for this engineer."}, status=404)
            asset = service.ro_asset
            company = service.company or service.customer.company
        else:
            return Response({"detail": "RO health access is not available for this role."}, status=403)

        return Response(asset_health(company, asset, configuration_key))


class ServiceIntervalPolicyAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        company = _active_company_for(request.user)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        policies = ServiceIntervalPolicy.objects.filter(company=company).select_related("part", "ro_model")
        return Response([
            {
                "id": policy.id,
                "part_id": policy.part_id,
                "part_name": policy.part.name,
                "ro_model_id": policy.ro_model_id,
                "ro_model": policy.ro_model.model_name if policy.ro_model_id else None,
                "configuration_key": policy.configuration_key,
                "interval_days": policy.interval_days,
                "due_soon_days": policy.due_soon_days,
                "reminder_days": policy.reminder_days,
                "is_active": policy.is_active,
            }
            for policy in policies
        ])

    @transaction.atomic
    def post(self, request):
        company = _active_company_for(request.user)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)

        try:
            part_id = int(request.data.get("part_id"))
            interval_days = int(request.data.get("interval_days"))
            due_soon_days = int(request.data.get("due_soon_days", 30))
        except (TypeError, ValueError):
            return Response({"detail": "part_id and valid interval days are required."}, status=400)
        if interval_days <= 0 or due_soon_days < 0:
            return Response({"detail": "Intervals must be positive and due-soon days cannot be negative."}, status=400)

        part = get_object_or_404(PartMaster, pk=part_id, is_active=True)
        ro_model = None
        ro_model_id = request.data.get("ro_model_id")
        if ro_model_id not in (None, ""):
            ro_model = get_object_or_404(ROModel, pk=ro_model_id, is_active=True)

        raw_reminders = request.data.get("reminder_days", [])
        if not isinstance(raw_reminders, list):
            return Response({"detail": "reminder_days must be a list."}, status=400)
        reminders = []
        for raw in raw_reminders:
            try:
                day = int(raw)
            except (TypeError, ValueError):
                return Response({"detail": "Every reminder day must be a number."}, status=400)
            if day < 0 or day > 3650:
                return Response({"detail": "Reminder days must be between 0 and 3650."}, status=400)
            if day not in reminders:
                reminders.append(day)
        reminders.sort(reverse=True)

        configuration_key = str(request.data.get("configuration_key", "") or "").strip()[:80]
        policy, created = ServiceIntervalPolicy.objects.update_or_create(
            company=company,
            part=part,
            ro_model=ro_model,
            configuration_key=configuration_key,
            defaults={
                "interval_days": interval_days,
                "due_soon_days": due_soon_days,
                "reminder_days": reminders,
                "is_active": bool(request.data.get("is_active", True)),
            },
        )
        return Response(
            {
                "success": True,
                "created": created,
                "policy_id": policy.id,
                "part_id": policy.part_id,
                "ro_model_id": policy.ro_model_id,
                "configuration_key": policy.configuration_key,
                "interval_days": policy.interval_days,
                "due_soon_days": policy.due_soon_days,
                "reminder_days": policy.reminder_days,
                "is_active": policy.is_active,
            },
            status=201 if created else 200,
        )


class ServiceSearchAPIView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        keyword = self.request.GET.get("q", "").strip()
        queryset = _service_queryset_for(self.request.user)

        if keyword:
            queryset = queryset.filter(
                Q(service_id__icontains=keyword)
                | Q(customer__name__icontains=keyword)
                | Q(customer__phone__icontains=keyword)
                | Q(customer__card_number__icontains=keyword)
            )

        return queryset.order_by("-id")


class ServiceExportAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request, *args, **kwargs):
        queryset = _service_queryset_for(request.user).order_by("-id")
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Service Report"

        worksheet.append([
            "ID",
            "Service ID",
            "Customer",
            "Customer Phone",
            "Engineer",
            "Asset",
            "Service Type",
            "Status",
            "Scheduled Date",
            "Completed Date",
            "Next Service Date",
            "Input TDS",
            "Output TDS",
            "Remarks",
            "Latitude",
            "Longitude",
        ])

        for service in queryset:
            worksheet.append([
                service.id,
                service.service_id,
                service.customer.name if service.customer else "",
                service.customer.phone if service.customer else "",
                service.engineer.name if service.engineer else "",
                service.ro_asset.asset_id if service.ro_asset else "",
                service.service_type,
                service.status,
                service.scheduled_date.isoformat() if service.scheduled_date else "",
                service.completed_date.isoformat() if service.completed_date else "",
                service.next_service_date.isoformat() if service.next_service_date else "",
                service.input_tds or "",
                service.output_tds or "",
                service.remarks,
                service.latitude or "",
                service.longitude or "",
            ])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="service_report.xlsx"'
        return response
