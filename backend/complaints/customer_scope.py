from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from customers.models import Customer
from customers.identity import unique_unlinked_customer_for_phone
from tenancy.access import has_feature_access, request_company

from .models import Complaint
from .views import (
    ComplaintCreateAPIView,
    ComplaintDetailAPIView,
    ComplaintListAPIView,
    ComplaintSearchAPIView,
    restrict_complaints_for_user,
)


def linked_customer_for_complaints(user):
    if (
        not user
        or not user.is_authenticated
        or getattr(user, "role", None) != "CUSTOMER"
        or not user.is_verified
        or not user.is_active
    ):
        return None

    linked = Customer.objects.filter(user=user, is_active=True).first()
    if linked is not None:
        return linked

    legacy = unique_unlinked_customer_for_phone(user.phone, active_only=True)
    if legacy is not None:
        legacy.user = user
        legacy.save(update_fields=["user"])
    return legacy


def _complaint_module_allowed(request):
    user = request.user
    if getattr(user, "role", None) == "CUSTOMER":
        return bool(user.is_verified and user.is_active)
    return has_feature_access(request, "complaint")


def secure_complaint_queryset(queryset, request):
    user = request.user
    role = getattr(user, "role", None)

    if role == "CUSTOMER":
        customer = linked_customer_for_complaints(user)
        return queryset.filter(customer=customer) if customer is not None else queryset.none()

    if not has_feature_access(request, "complaint"):
        return queryset.none()

    company = request_company(request)

    if role == "ENGINEER":
        scoped = queryset.filter(engineer__user=user)
        if company is not None:
            scoped = scoped.filter(
                Q(company=company)
                | Q(company__isnull=True, customer__company=company)
                | Q(company__isnull=True, engineer__company=company)
            )
        return scoped

    if company is not None:
        return queryset.filter(
            Q(company=company)
            | Q(company__isnull=True, customer__company=company)
            | Q(company__isnull=True, engineer__company=company)
        ).distinct()

    return queryset.filter(company__isnull=True)


def _effective_customer_company_id(customer):
    if customer is None:
        return None
    if customer.company_id is not None:
        return customer.company_id
    if customer.assigned_engineer_id:
        return customer.assigned_engineer.company_id
    return None


def _validate_workspace(company, customer, engineer=None):
    customer_company_id = _effective_customer_company_id(customer)
    if company is None:
        if customer_company_id is not None:
            raise ValidationError({"customer": ["Customer belongs to a company workspace."]})
        if engineer is not None and engineer.company_id is not None:
            raise ValidationError({"engineer": ["Engineer belongs to a company workspace."]})
        return

    if customer_company_id != company.id:
        raise ValidationError({
            "customer": ["Customer ownership is unresolved or outside the active workspace."]
        })
    if engineer is not None and engineer.company_id != company.id:
        raise ValidationError({"engineer": ["Engineer is outside the active workspace."]})


class SecureComplaintListAPIView(ComplaintListAPIView):
    def get(self, request, *args, **kwargs):
        if not _complaint_module_allowed(request):
            return Response(
                {"detail": "Complaint module permission is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Complaint.objects.select_related(
            "customer", "engineer__user", "linked_service"
        ).order_by("-id")
        return secure_complaint_queryset(queryset, self.request)


class SecureComplaintDetailAPIView(ComplaintDetailAPIView):
    def get(self, request, *args, **kwargs):
        if not _complaint_module_allowed(request):
            return Response(
                {"detail": "Complaint module permission is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Complaint.objects.select_related(
            "customer", "engineer__user", "linked_service"
        )
        return secure_complaint_queryset(queryset, self.request)


class SecureComplaintSearchAPIView(ComplaintSearchAPIView):
    def get(self, request, *args, **kwargs):
        if not _complaint_module_allowed(request):
            return Response(
                {"detail": "Complaint module permission is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        keyword = self.request.GET.get("q", "").strip()
        queryset = secure_complaint_queryset(
            Complaint.objects.select_related(
                "customer", "engineer__user", "linked_service"
            ),
            self.request,
        )
        if keyword:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(complaint_id__icontains=keyword)
                | Q(customer__name__icontains=keyword)
                | Q(customer__phone__icontains=keyword)
                | Q(description__icontains=keyword)
            )
        return queryset.order_by("-id")


class SecureComplaintCreateAPIView(ComplaintCreateAPIView):
    """Preserve original complaint workflow while enforcing explicit tenant ownership."""

    def perform_create(self, serializer):
        role = getattr(self.request.user, "role", None)
        if role != "CUSTOMER" and not has_feature_access(self.request, "complaint"):
            raise PermissionDenied("Complaint module permission is required.")

        if role == "CUSTOMER":
            customer = linked_customer_for_complaints(self.request.user)
            if customer is None:
                raise ValidationError({
                    "customer": ["Customer account is not linked to a customer record."]
                })
            serializer.save(
                customer=customer,
                company=customer.company,
                engineer=None,
                priority="NORMAL",
                latitude=customer.latitude,
                longitude=customer.longitude,
            )
            return

        company = request_company(self.request)
        customer = serializer.validated_data.get("customer")

        if role == "ENGINEER":
            employee = getattr(self.request.user, "employee_profile", None)
            if (
                customer is None
                or employee is None
                or customer.assigned_engineer_id != employee.id
            ):
                raise ValidationError({
                    "customer": ["You can create complaints only for customers assigned to you."]
                })
            _validate_workspace(company, customer, employee)
            location = {}
            if serializer.validated_data.get("latitude") is None:
                location["latitude"] = customer.latitude
            if serializer.validated_data.get("longitude") is None:
                location["longitude"] = customer.longitude
            serializer.save(
                company=company,
                engineer=employee,
                **location,
            )
            return

        engineer = serializer.validated_data.get("engineer")
        _validate_workspace(company, customer, engineer)
        location = {}
        if customer is not None:
            if serializer.validated_data.get("latitude") is None:
                location["latitude"] = customer.latitude
            if serializer.validated_data.get("longitude") is None:
                location["longitude"] = customer.longitude
        serializer.save(company=company, **location)
