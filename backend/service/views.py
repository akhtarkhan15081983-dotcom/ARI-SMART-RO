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

from accounts.permissions import user_role
from tenancy.access import HasRequiredFeature, has_feature_access, request_company
from customers.models import Customer
from customers.identity import unique_unlinked_customer_for_phone
from .models import Service
from .serializers import ServiceSerializer


def _linked_customer_for(user):
    """Resolve exactly one customer record for a verified customer account.

    Shared/duplicate phone numbers are valid ARI business data, so phone alone
    must never grant access to every record with that number. Prefer the durable
    user link; phone-only fallback is allowed only when exactly one unlinked row exists.
    """
    if user_role(user) != "CUSTOMER" or not user.is_verified or not user.is_active:
        return None

    linked = Customer.objects.filter(user=user, is_active=True).first()
    if linked is not None:
        return linked

    legacy = unique_unlinked_customer_for_phone(user.phone, active_only=True)
    if legacy is not None:
        legacy.user = user
        legacy.save(update_fields=["user"])
    return legacy


def _service_module_allowed(request):
    role = user_role(request.user)
    if role == "CUSTOMER":
        return bool(request.user.is_verified and request.user.is_active)
    return has_feature_access(request, "service")


def _service_queryset_for(request, include_customer=True):
    user = request.user
    queryset = Service.objects.select_related(
        "customer",
        "engineer",
        "engineer__user",
        "ro_asset",
    )
    role = user_role(user)

    if include_customer and role == "CUSTOMER":
        customer = _linked_customer_for(user)
        return queryset.filter(customer=customer) if customer is not None else queryset.none()

    if not has_feature_access(request, "service"):
        return queryset.none()

    company = request_company(request)
    if role == "ENGINEER":
        scoped = queryset.filter(engineer__user=user)
        if company is not None:
            scoped = scoped.filter(
                Q(company=company)
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


class ServiceListAPIView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not _service_module_allowed(request):
            return Response(
                {"detail": "Service module permission is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return _service_queryset_for(self.request).order_by("-id")


class ServiceCreateAPIView(generics.CreateAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "service"


class ServiceDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not _service_module_allowed(request):
            return Response(
                {"detail": "Service module permission is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return _service_queryset_for(self.request)


class ServiceUpdateAPIView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "service"

    def get_queryset(self):
        return _service_queryset_for(self.request, include_customer=False)


class CompleteServiceAPIView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "service"

    def get_queryset(self):
        return _service_queryset_for(self.request, include_customer=False)

    @transaction.atomic
    def _complete(self):
        service = get_object_or_404(
            self.get_queryset().select_for_update(), pk=self.kwargs["pk"]
        )
        self.check_object_permissions(self.request, service)
        if service.status == "COMPLETED":
            return Response({
                "success": True,
                "service_id": service.service_id,
                "message": "Service completed successfully.",
            }, status=status.HTTP_200_OK)
        service.status = "COMPLETED"
        service.completed_date = timezone.now()
        service.save(update_fields=["status", "completed_date", "updated_at"])
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


class ServiceSearchAPIView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not _service_module_allowed(request):
            return Response(
                {"detail": "Service module permission is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        keyword = self.request.GET.get("q", "").strip()
        queryset = _service_queryset_for(self.request)

        if keyword:
            queryset = queryset.filter(
                Q(service_id__icontains=keyword)
                | Q(customer__name__icontains=keyword)
                | Q(customer__phone__icontains=keyword)
                | Q(customer__card_number__icontains=keyword)
            )

        return queryset.order_by("-id")


class ServiceExportAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "service"

    def get(self, request, *args, **kwargs):
        queryset = _service_queryset_for(request).order_by("-id")
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
                service.ro_asset.name if service.ro_asset else "",
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
