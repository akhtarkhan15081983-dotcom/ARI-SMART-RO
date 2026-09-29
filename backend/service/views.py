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

from accounts.permissions import IsOperationsUser, IsStaffOperator, STAFF_ROLES, user_role
from customers.models import Customer
from .models import Service
from .serializers import ServiceSerializer


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


def _service_queryset_for(user, include_customer=True):
    queryset = Service.objects.select_related(
        "customer",
        "engineer",
        "engineer__user",
        "ro_asset",
    )
    role = user_role(user)

    if role in STAFF_ROLES:
        return queryset
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
