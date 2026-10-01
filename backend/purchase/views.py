from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers, viewsets

from accounts.permissions import IsStaffOperator
from jobs.idempotency import action_id_from_request, replay_response, remember_response
from tenancy.access import HasRequiredFeature, request_company

from .invoice_identity import supplier_invoice_exists
from .models import Supplier, Purchase, PurchaseItem
from .retry_identity import purchase_action_type
from .serializers import SupplierSerializer, PurchaseSerializer, PurchaseItemSerializer


def _scope_for_request(request, queryset):
    company = request_company(request)
    if company is not None:
        return queryset.filter(company=company)
    return queryset.filter(company__isnull=True)


class SupplierViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    def get_queryset(self):
        return _scope_for_request(self.request, Supplier.objects.all())

    def perform_create(self, serializer):
        serializer.save(company=request_company(self.request))


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    def get_queryset(self):
        return _scope_for_request(
            self.request,
            Purchase.objects.select_related("supplier").prefetch_related("items"),
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        company = request_company(request)
        action_id = action_id_from_request(request)
        if not action_id:
            return super().create(request, *args, **kwargs)
        # Serialize retries by this user even when a blank invoice would
        # generate different NO-BILL values in concurrent requests.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        action_type = purchase_action_type(
            "purchase_manual", company.id if company else None, request.data,
        )
        replay = replay_response(request=request, action_type=action_type)
        if replay.response is not None:
            return replay.response
        response = super().create(request, *args, **kwargs)
        return remember_response(
            request=request, action_id=action_id,
            action_type=action_type, response=response,
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
        if invoice_number and supplier_invoice_exists(
            company_id=expected_company_id,
            supplier_id=supplier.id,
            invoice_number=invoice_number,
        ):
            raise serializers.ValidationError(
                {"invoice_number": "This supplier invoice already exists in this workspace."}
            )
        serializer.save(company=company, supplier=supplier)


class PurchaseItemViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseItemSerializer
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return _scope_for_request(
            self.request,
            PurchaseItem.objects.select_related("purchase", "part"),
        )
