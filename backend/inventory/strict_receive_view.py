from django.db import models, transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffOperator
from purchase.models import PurchaseItem
from tenancy.access import request_company

from .models import InventoryAuditLog, InventoryItem


class StrictTenantScopedInventoryReceiveAPIView(APIView):
    """Receive serialized stock without leaking or mutating another workspace."""

    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        company = request_company(request)
        company_id = company.id if company is not None else None
        purchase_item_id = request.data.get("purchase_item_id")
        code = str(request.data.get("code", "")).strip()
        if not code or len(code) > 100:
            return Response(
                {"success": False, "message": "Scan or enter a valid QR/serial code."},
                status=400,
            )

        purchase_item = (
            PurchaseItem.objects.filter(company_id=company_id, pk=purchase_item_id)
            .select_related("purchase", "part")
            .first()
        )
        if purchase_item is None:
            return Response(
                {"success": False, "message": "Purchase item not found in this workspace."},
                status=404,
            )
        if not purchase_item.part.is_serialized:
            return Response(
                {"success": False, "message": "This item uses photo receipt, not QR scanning."},
                status=400,
            )

        # Serial numbers are globally unique physical identifiers. Never reveal
        # which other workspace owns a collision.
        if InventoryItem.objects.exclude(company_id=company_id).filter(
            models.Q(serial_number=code) | models.Q(barcode=code)
        ).exists():
            return Response(
                {"success": False, "message": "This QR/serial code is unavailable."},
                status=409,
            )

        registered = (
            InventoryItem.objects.select_for_update()
            .filter(
                company_id=company_id,
                purchase_item=purchase_item,
                status="PENDING_RECEIPT",
            )
            .filter(models.Q(serial_number=code) | models.Q(barcode=code))
            .first()
        )
        inventory_item = registered or (
            InventoryItem.objects.select_for_update()
            .filter(
                company_id=company_id,
                purchase_item=purchase_item,
                status="PENDING_RECEIPT",
                part__is_serialized=True,
            )
            .filter(models.Q(serial_number__isnull=True) | models.Q(serial_number=""))
            .select_related("part", "purchase_item__purchase")
            .first()
        )
        if inventory_item is None:
            return Response(
                {"success": False, "message": "No pending quantity remains for this purchase item."},
                status=409,
            )

        inventory_item.serial_number = code
        inventory_item.barcode = code
        inventory_item.status = "IN_STOCK"
        inventory_item.received_at = timezone.now()
        inventory_item.received_by = request.user
        inventory_item.save()
        InventoryAuditLog.objects.create(
            company_id=company_id,
            inventory_item=inventory_item,
            performed_by=request.user,
            action="RECEIVED",
            old_status="PENDING_RECEIPT",
            new_status="IN_STOCK",
            serial_number=code,
            remarks=f"Received against invoice {purchase_item.purchase.invoice_number}",
        )
        return Response(
            {
                "success": True,
                "message": "Part received into stock.",
                "inventory_item_id": inventory_item.id,
                "part": inventory_item.part.name,
                "serial_number": code,
            },
            status=201,
        )
