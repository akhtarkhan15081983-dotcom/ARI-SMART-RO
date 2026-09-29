from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffOperator
from employees.models import EmployeeProfile
from jobs.idempotency import replay_response, remember_response
from tenancy.access import request_company

from .models import EngineerBagItem, InventoryAuditLog, InventoryItem
from .serializers import EngineerBagIssueSerializer


def _company_id(request):
    company = request_company(request)
    return company.id if company is not None else None


class ReissuableTenantScopedEngineerBagIssueAPIView(generics.CreateAPIView):
    """Issue company stock and safely reuse a returned one-to-one bag record."""

    serializer_class = EngineerBagIssueSerializer
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        company_id = _company_id(request)
        try:
            engineer_id = int(request.data.get("engineer"))
            inventory_item_id = int(request.data.get("inventory_item"))
        except (TypeError, ValueError):
            return Response({"error": "Engineer and inventory item are required."}, status=400)

        engineer = get_object_or_404(
            EmployeeProfile.objects.select_for_update(),
            pk=engineer_id,
            company_id=company_id,
            is_active=True,
            user__is_active=True,
        )
        inventory_item = get_object_or_404(
            InventoryItem.objects.select_for_update().select_related("part"),
            pk=inventory_item_id,
            company_id=company_id,
        )
        if inventory_item.status != "IN_STOCK":
            InventoryAuditLog.objects.create(
                company_id=company_id,
                inventory_item=inventory_item,
                performed_by=request.user,
                action="SECURITY_REJECT",
                old_status=inventory_item.status,
                new_status=inventory_item.status,
                serial_number=inventory_item.serial_number or "",
                remarks="Attempted to issue inventory that was not in stock.",
            )
            return Response({"error": "Part is not available in stock."}, status=400)
        if inventory_item.part.is_serialized and not inventory_item.serial_number:
            return Response(
                {"error": "Serialized part must have a serial number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bag_item = (
            EngineerBagItem.objects.select_for_update()
            .filter(inventory_item=inventory_item)
            .first()
        )
        if bag_item is not None:
            if bag_item.status != "RETURNED":
                return Response(
                    {"error": "This physical part is already linked to an active engineer bag."},
                    status=status.HTTP_409_CONFLICT,
                )
            bag_item.company_id = company_id
            bag_item.engineer = engineer
            bag_item.status = "ISSUED"
            bag_item.issue_date = timezone.now()
            bag_item.install_date = None
            bag_item.return_date = None
            bag_item.remarks = str(request.data.get("remarks", ""))
            bag_item.save(
                update_fields=[
                    "company",
                    "engineer",
                    "status",
                    "issue_date",
                    "install_date",
                    "return_date",
                    "remarks",
                ]
            )
        else:
            bag_item = EngineerBagItem.objects.create(
                company_id=company_id,
                engineer=engineer,
                inventory_item=inventory_item,
                status="ISSUED",
                remarks=str(request.data.get("remarks", "")),
            )

        old_status = inventory_item.status
        inventory_item.status = "ISSUED"
        inventory_item.save(update_fields=["status"])
        InventoryAuditLog.objects.create(
            company_id=company_id,
            inventory_item=inventory_item,
            engineer=engineer,
            performed_by=request.user,
            action="ISSUED",
            old_status=old_status,
            new_status="ISSUED",
            serial_number=inventory_item.serial_number or "",
            remarks=str(request.data.get("remarks", "")),
        )
        return Response(EngineerBagIssueSerializer(bag_item).data, status=status.HTTP_201_CREATED)


class TenantScopedEngineerBagReturnAPIView(APIView):
    """Return an issued physical part to warehouse stock atomically."""

    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        company_id = _company_id(request)
        try:
            inventory_item_id = int(request.data.get("inventory_item"))
        except (TypeError, ValueError):
            return Response({"error": "Inventory item is required."}, status=400)

        inventory_item = get_object_or_404(
            InventoryItem.objects.select_for_update(),
            pk=inventory_item_id,
            company_id=company_id,
        )
        action_type = f"inventory_return:{inventory_item.id}"
        replay = replay_response(request=request, action_type=action_type)
        if replay.response is not None:
            return replay.response
        bag_item = (
            EngineerBagItem.objects.select_for_update()
            .filter(
                inventory_item=inventory_item,
                company_id=company_id,
                engineer__company_id=company_id,
                status="ISSUED",
            )
            .select_related("engineer")
            .first()
        )
        if bag_item is None or inventory_item.status != "ISSUED":
            return Response(
                {"error": "Only currently issued company stock can be returned."},
                status=status.HTTP_409_CONFLICT,
            )

        bag_item.status = "RETURNED"
        bag_item.return_date = timezone.now()
        bag_item.save(update_fields=["status", "return_date"])

        inventory_item.status = "IN_STOCK"
        inventory_item.save(update_fields=["status"])

        InventoryAuditLog.objects.create(
            company_id=company_id,
            inventory_item=inventory_item,
            engineer=bag_item.engineer,
            performed_by=request.user,
            action="RETURNED",
            old_status="ISSUED",
            new_status="IN_STOCK",
            serial_number=inventory_item.serial_number or "",
            remarks=str(request.data.get("remarks", "")),
        )
        response = Response(
            {
                "success": True,
                "inventory_item": inventory_item.id,
                "inventory_status": inventory_item.status,
                "bag_status": bag_item.status,
            },
            status=status.HTTP_200_OK,
        )
        return remember_response(
            request=request, action_id=replay.action_id,
            action_type=action_type, response=response,
        )
