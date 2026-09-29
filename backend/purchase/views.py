from django.db import transaction
from rest_framework import serializers, viewsets

from accounts.permissions import IsStaffOperator
from tenancy.access import request_company

from .models import Supplier, Purchase, PurchaseItem
from .serializers import SupplierSerializer, PurchaseSerializer, PurchaseItemSerializer


def _scope_for_request(request, queryset):
    company = request_company(request)
    if company is not None:
        return queryset.filter(company=company)
    return queryset.filter(company__isnull=True)


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [IsStaffOperator]

    def get_queryset(self):
        return _scope_for_request(self.request, Supplier.objects.all())

    def perform_create(self, serializer):
        serializer.save(company=request_company(self.request))


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [IsStaffOperator]

    def get_queryset(self):
        return _scope_for_request(
            self.request,
            Purchase.objects.select_related("supplier").prefetch_related("items"),
        )

    @transaction.atomic
    def perform_create(self, serializer):
        company = request_company(self.request)
        expected_company_id = company.id if company is not None else None
        supplied = serializer.validated_data["supplier"]
        supplier = Supplier.objects.select_for_update().filter(
            pk=supplied.pk,
            company_id=expected_company_id,
            is_active=True,
        ).first()
        if supplier is None:
            raise serializers.ValidationError(
                {"supplier": "Supplier does not belong to this workspace."}
            )

        invoice_number = str(serializer.validated_data.get("invoice_number") or "").strip()
        if invoice_number and Purchase.objects.filter(
            company_id=expected_company_id,
            supplier=supplier,
            invoice_number__iexact=invoice_number,
        ).exists():
            raise serializers.ValidationError(
                {"invoice_number": "This supplier invoice already exists in this workspace."}
            )
        serializer.save(company=company, supplier=supplier)


class PurchaseItemViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsStaffOperator]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return _scope_for_request(
            self.request,
            PurchaseItem.objects.select_related("purchase", "part"),
        )
