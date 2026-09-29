from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response

from employees.models import EmployeeProfile
from tenancy.access import request_company

from .models import EngineerBagItem, InventoryAuditLog, InventoryItem, PartRequest, PartRequestEvent
from .serializers import EngineerBagIssueSerializer
from .views import (
    AdminEngineerBagAPIView,
    EngineerBagIssueAPIView,
    MyBagAPIView,
    MyPartRequestsAPIView,
    PartRequestApprovalInboxAPIView,
    PartRequestFulfilAPIView,
    PartRequestReviewAPIView,
    _request_payload,
)


def _expected_company_id(request):
    company = request_company(request)
    return company.id if company is not None else None


def _employee_in_request_workspace(request, employee_id):
    expected_company_id = _expected_company_id(request)
    queryset = EmployeeProfile.objects.filter(
        pk=employee_id,
        is_active=True,
        user__is_active=True,
    )
    return queryset.filter(company_id=expected_company_id).exists()


def _part_request_in_request_workspace(request, request_id):
    expected_company_id = _expected_company_id(request)
    return PartRequest.objects.filter(
        pk=request_id,
        company_id=expected_company_id,
        engineer__company_id=expected_company_id,
    ).exists()


class TenantScopedEngineerBagIssueAPIView(EngineerBagIssueAPIView):
    """Issue only stock and engineer records owned by the active workspace."""

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        expected_company_id = _expected_company_id(request)
        try:
            engineer_id = int(request.data.get("engineer"))
            inventory_item_id = int(request.data.get("inventory_item"))
        except (TypeError, ValueError):
            return Response({"error": "Engineer and inventory item are required."}, status=400)

        engineer = get_object_or_404(
            EmployeeProfile.objects.select_for_update(),
            pk=engineer_id,
            company_id=expected_company_id,
            is_active=True,
            user__is_active=True,
        )
        inventory_item = get_object_or_404(
            InventoryItem.objects.select_for_update().select_related("part"),
            pk=inventory_item_id,
            company_id=expected_company_id,
        )
        if inventory_item.status != "IN_STOCK":
            InventoryAuditLog.objects.create(
                company_id=expected_company_id,
                inventory_item=inventory_item,
                performed_by=request.user,
                action="SECURITY_REJECT",
                old_status=inventory_item.status,
                new_status=inventory_item.status,
                serial_number=inventory_item.serial_number or "",
                remarks="Attempted to issue inventory that was not in stock.",
            )
            return Response({"error": "Part is not available in stock."}, status=400)
        if EngineerBagItem.objects.filter(inventory_item=inventory_item, status="ISSUED").exists():
            return Response({"error": "This physical part is already issued to an engineer."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["engineer"].id != engineer.id:
            return Response({"error": "Engineer mismatch."}, status=400)
        if serializer.validated_data["inventory_item"].id != inventory_item.id:
            return Response({"error": "Inventory item mismatch."}, status=400)

        bag_item = serializer.save(company_id=expected_company_id, status="ISSUED")
        old_status = inventory_item.status
        inventory_item.status = "ISSUED"
        inventory_item.save(update_fields=["status"])
        InventoryAuditLog.objects.create(
            company_id=expected_company_id,
            inventory_item=inventory_item,
            engineer=engineer,
            performed_by=request.user,
            action="ISSUED",
            old_status=old_status,
            new_status="ISSUED",
            serial_number=inventory_item.serial_number or "",
            remarks=request.data.get("remarks", ""),
        )
        return Response(EngineerBagIssueSerializer(bag_item).data, status=status.HTTP_201_CREATED)


class TenantScopedMyBagAPIView(MyBagAPIView):
    def get_queryset(self):
        expected_company_id = _expected_company_id(self.request)
        return super().get_queryset().filter(
            company_id=expected_company_id,
            engineer__company_id=expected_company_id,
            inventory_item__company_id=expected_company_id,
        )


class TenantScopedAdminEngineerBagAPIView(AdminEngineerBagAPIView):
    def get_queryset(self):
        expected_company_id = _expected_company_id(self.request)
        return super().get_queryset().filter(
            company_id=expected_company_id,
            engineer__company_id=expected_company_id,
            inventory_item__company_id=expected_company_id,
        )


class TenantScopedMyPartRequestsAPIView(MyPartRequestsAPIView):
    def get_queryset(self):
        expected_company_id = _expected_company_id(self.request)
        return super().get_queryset().filter(company_id=expected_company_id)

    def perform_create(self, serializer):
        expected_company_id = _expected_company_id(self.request)
        engineer = get_object_or_404(
            EmployeeProfile,
            user=self.request.user,
            designation="ENGINEER",
            is_active=True,
            company_id=expected_company_id,
        )
        part_request = serializer.save(
            engineer=engineer,
            company_id=expected_company_id,
        )
        PartRequestEvent.objects.create(
            part_request=part_request,
            action="CREATED",
            performed_by=self.request.user,
            remarks=part_request.remarks,
            metadata={"company_id": expected_company_id},
        )


class TenantScopedPartRequestApprovalInboxAPIView(PartRequestApprovalInboxAPIView):
    def get(self, request):
        expected_company_id = _expected_company_id(request)
        queryset = PartRequest.objects.select_related("part", "engineer__user").filter(
            company_id=expected_company_id,
            engineer__company_id=expected_company_id,
        ).order_by("-created_at")
        status_filter = str(request.query_params.get("status", "")).upper()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response({"success": True, "requests": [_request_payload(row) for row in queryset[:250]]})


class TenantScopedPartRequestReviewAPIView(PartRequestReviewAPIView):
    def post(self, request, request_id):
        if not _part_request_in_request_workspace(request, request_id):
            return Response(
                {"success": False, "message": "Part request not found in this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().post(request, request_id)


class TenantScopedPartRequestFulfilAPIView(PartRequestFulfilAPIView):
    """Fulfil requests only from verified stock owned by the same company."""

    @transaction.atomic
    def post(self, request, request_id):
        expected_company_id = _expected_company_id(request)
        part_request = get_object_or_404(
            PartRequest.objects.select_for_update().select_related("engineer", "part"),
            id=request_id,
            company_id=expected_company_id,
            engineer__company_id=expected_company_id,
        )
        if part_request.status != "APPROVED":
            return Response({"success": False, "message": "Only approved requests can be issued."}, status=409)

        codes = request.data.get("codes") or []
        stock_queryset = InventoryItem.objects.select_for_update().filter(
            company_id=expected_company_id,
            part=part_request.part,
            status="IN_STOCK",
        )
        if part_request.part.is_serialized:
            if not isinstance(codes, list) or len(codes) != part_request.quantity:
                return Response({"success": False, "message": f"Scan exactly {part_request.quantity} part code(s)."}, status=400)
            clean_codes = [str(code).strip() for code in codes]
            if len(set(clean_codes)) != len(clean_codes):
                return Response({"success": False, "message": "Duplicate QR codes are not allowed."}, status=400)
            stock = list(stock_queryset.filter(serial_number__in=clean_codes))
        else:
            stock = list(
                stock_queryset.filter(receipt_photo__isnull=False)
                .order_by("received_at", "id")[:part_request.quantity]
            )

        if len(stock) != part_request.quantity:
            return Response({"success": False, "message": "Required verified stock is not available."}, status=409)

        for item in stock:
            EngineerBagItem.objects.create(
                company_id=expected_company_id,
                engineer=part_request.engineer,
                inventory_item=item,
                status="ISSUED",
                remarks=f"Issued against part request #{part_request.id}",
            )
            item.status = "ISSUED"
            item.save(update_fields=["status"])
            InventoryAuditLog.objects.create(
                company_id=expected_company_id,
                inventory_item=item,
                engineer=part_request.engineer,
                performed_by=request.user,
                action="ISSUED",
                old_status="IN_STOCK",
                new_status="ISSUED",
                serial_number=item.serial_number or "",
                remarks=f"Part request #{part_request.id}",
            )

        part_request.status = "FULFILLED"
        part_request.save(update_fields=["status"])
        PartRequestEvent.objects.create(
            part_request=part_request,
            action="FULFILLED",
            performed_by=request.user,
            remarks="Parts issued from company-owned verified stock.",
            metadata={"company_id": expected_company_id},
        )
        return Response({"success": True, "message": "Part request fulfilled."})
