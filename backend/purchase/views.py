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

    def perform_create(self, serializer):
        company = request_company(self.request)
        supplier = serializer.validated_data["supplier"]
        if supplier.company_id != (company.id if company is not None else None):
            raise serializers.ValidationError({"supplier": "Supplier does not belong to this workspace."})
        serializer.save(company=company)


class PurchaseItemViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsStaffOperator]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return _scope_for_request(
            self.request,
            PurchaseItem.objects.select_related("purchase", "part"),
        )
