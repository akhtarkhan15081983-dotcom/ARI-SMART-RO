from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from tenancy.access import HasRequiredFeature, request_company
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from accounts.permissions import IsStaffOperator

from .serializers import OCRVerifySerializer, EngineerBagIssueSerializer, MyBagSerializer, PartRequestSerializer, PartCatalogSerializer
from .models import InventoryItem, EngineerBagItem, InventoryAuditLog, PartRequest, PartRequestEvent
from purchase.models import PurchaseItem
from partmaster.models import PartMaster
from employees.models import EmployeeProfile
from accounts.permissions import IsAdminOrManager


class EngineerBagIssueAPIView(generics.CreateAPIView):
    serializer_class = EngineerBagIssueSerializer
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        inventory_item = get_object_or_404(InventoryItem.objects.select_for_update(), id=request.data.get("inventory_item"))
        if inventory_item.status != "IN_STOCK":
            InventoryAuditLog.objects.create(inventory_item=inventory_item, performed_by=request.user, action="SECURITY_REJECT", old_status=inventory_item.status, new_status=inventory_item.status, serial_number=inventory_item.serial_number or "", remarks="Attempted to issue an inventory item that was not in stock.")
            return Response({"error": "Part is not available in stock."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        engineer = serializer.validated_data["engineer"]
        if EngineerBagItem.objects.filter(inventory_item=inventory_item, status="ISSUED").exists():
            InventoryAuditLog.objects.create(inventory_item=inventory_item, engineer=engineer, performed_by=request.user, action="SECURITY_REJECT", old_status=inventory_item.status, new_status=inventory_item.status, serial_number=inventory_item.serial_number or "", remarks="Duplicate issue attempt detected.")
            return Response({"error": "This physical part is already issued to an engineer."}, status=status.HTTP_400_BAD_REQUEST)
        bag_item = serializer.save(status="ISSUED")
        old_status = inventory_item.status
        inventory_item.status = "ISSUED"
        inventory_item.save(update_fields=["status"])
        InventoryAuditLog.objects.create(inventory_item=inventory_item, engineer=engineer, performed_by=request.user, action="ISSUED", old_status=old_status, new_status="ISSUED", serial_number=inventory_item.serial_number or "", remarks=request.data.get("remarks", ""))
        return Response(EngineerBagIssueSerializer(bag_item).data, status=status.HTTP_201_CREATED)


class OCRVerifyAPIView(generics.GenericAPIView):
    serializer_class = OCRVerifySerializer
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "qr"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        engineer = EmployeeProfile.objects.filter(
            user=request.user,
            is_active=True,
            user__is_active=True,
        ).first()
        if engineer is None:
            return Response(
                {"verified": False, "message": "Active employee profile is required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serial_number = serializer.validated_data["serial_number"].strip()
        bag_item = EngineerBagItem.objects.select_related("inventory_item", "inventory_item__part", "engineer__user").filter(engineer=engineer, inventory_item__serial_number=serial_number, inventory_item__status="ISSUED", status="ISSUED").first()
        if not bag_item:
            issued_elsewhere = EngineerBagItem.objects.filter(
                engineer__company=engineer.company,
                inventory_item__serial_number=serial_number,
                inventory_item__status="ISSUED",
                status="ISSUED",
            ).exists()
            return Response(
                {
                    "verified": False,
                    "message": "This part is not currently issued to this engineer.",
                },
                status=(
                    status.HTTP_403_FORBIDDEN
                    if issued_elsewhere
                    else status.HTTP_400_BAD_REQUEST
                ),
            )
        return Response({"verified": True, "message": "Part verified successfully.", "inventory_item": bag_item.inventory_item.id, "part": bag_item.inventory_item.part.name, "part_code": bag_item.inventory_item.part.code, "serial_number": bag_item.inventory_item.serial_number})


class MyBagAPIView(generics.ListAPIView):
    serializer_class = MyBagSerializer
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "bag"

    def get_queryset(self):
        company = request_company(self.request)
        if company is None:
            return EngineerBagItem.objects.none()
        return EngineerBagItem.objects.select_related(
            "inventory_item__part", "engineer__user"
        ).filter(
            engineer__user=self.request.user,
            engineer__company=company,
            company=company,
            status="ISSUED",
            inventory_item__status="ISSUED",
        ).order_by("-issue_date")


class AdminEngineerBagAPIView(generics.ListAPIView):
    serializer_class = MyBagSerializer
    permission_classes = [IsAdminOrManager]

    def get_queryset(self):
        company = request_company(self.request)
        if company is None:
            return EngineerBagItem.objects.none()
        return EngineerBagItem.objects.select_related(
            "inventory_item__part", "engineer__user"
        ).filter(
            company=company,
            engineer__company=company,
            status="ISSUED",
            inventory_item__status="ISSUED",
            engineer__designation="ENGINEER",
            engineer__is_active=True,
        ).order_by("engineer__employee_id", "inventory_item__part__name")


class PartCatalogAPIView(generics.ListAPIView):
    serializer_class = PartCatalogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PartMaster.objects.filter(is_active=True).order_by("name")


class MyPartRequestsAPIView(generics.ListCreateAPIView):
    serializer_class = PartRequestSerializer
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "request"

    def get_queryset(self):
        company = request_company(self.request)
        if company is None:
            return PartRequest.objects.none()
        return PartRequest.objects.select_related("part", "engineer").filter(
            engineer__user=self.request.user,
            engineer__company=company,
            company=company,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        company = request_company(self.request)
        if company is None:
            raise PermissionDenied("Active company workspace not found.")
        engineer = get_object_or_404(
            EmployeeProfile,
            user=self.request.user,
            designation="ENGINEER",
            is_active=True,
            company=company,
        )
        part_request = serializer.save(engineer=engineer, company=company)
        PartRequestEvent.objects.create(
            part_request=part_request, action="CREATED", performed_by=self.request.user,
            remarks=part_request.remarks,
        )


def _company_id_for(user):
    membership = user.company_memberships.filter(is_active=True).first()
    return membership.company_id if membership else None


def _page_window(request, *, default_size=100, max_size=250):
    requested = "page" in request.query_params or "page_size" in request.query_params
    try:
        page = max(1, int(request.query_params.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size") or default_size)
    except (TypeError, ValueError):
        page_size = default_size
    page_size = min(max(page_size, 1), max_size)
    start = (page - 1) * page_size
    return requested, page, page_size, start, start + page_size


def _request_payload(part_request):
    return {
        "id": part_request.id,
        "engineer_id": part_request.engineer_id,
        "engineer_name": part_request.engineer.user.get_full_name() or part_request.engineer.user.phone,
        "employee_id": part_request.engineer.employee_id,
        "part_id": part_request.part_id,
        "part_name": part_request.part.name,
        "part_code": part_request.part.code,
        "quantity": part_request.quantity,
        "is_serialized": part_request.part.is_serialized,
        "remarks": part_request.remarks,
        "status": part_request.status,
        "review_remarks": part_request.review_remarks,
        "created_at": part_request.created_at,
        "reviewed_at": part_request.reviewed_at,
    }


class PartRequestApprovalInboxAPIView(APIView):
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    def get(self, request):
        queryset = PartRequest.objects.select_related("part", "engineer__user").order_by("-created_at")
        company_id = _company_id_for(request.user)
        if company_id:
            queryset = queryset.filter(engineer__company_id=company_id)
        status_filter = str(request.query_params.get("status", "")).upper()
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginated, page, page_size, start, end = _page_window(request)
        total_count = queryset.count()
        rows = [_request_payload(row) for row in queryset[start:end]]
        if not paginated:
            return Response({"success": True, "requests": rows})
        return Response({
            "success": True,
            "requests": rows,
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": end < total_count,
            "next_page": page + 1 if end < total_count else None,
        })


class PartRequestReviewAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, request_id):
        part_request = get_object_or_404(
            PartRequest.objects.select_for_update().select_related("engineer", "part"), id=request_id
        )
        company_id = _company_id_for(request.user)
        if company_id and part_request.engineer.company_id != company_id:
            return Response({"success": False, "message": "This request belongs to another company."}, status=403)
        if part_request.status != "PENDING":
            return Response({"success": False, "message": "Only pending requests can be reviewed."}, status=409)
        action = str(request.data.get("action", "")).upper()
        remarks = str(request.data.get("remarks", "")).strip()
        if action not in {"APPROVE", "REJECT"}:
            return Response({"success": False, "message": "Choose approve or reject."}, status=400)
        if action == "REJECT" and len(remarks) < 5:
            return Response({"success": False, "message": "Rejection reason is required."}, status=400)
        part_request.status = "APPROVED" if action == "APPROVE" else "REJECTED"
        part_request.reviewed_by = request.user
        part_request.reviewed_at = timezone.now()
        part_request.review_remarks = remarks
        part_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_remarks"])
        PartRequestEvent.objects.create(
            part_request=part_request, action=part_request.status,
            performed_by=request.user, remarks=remarks,
        )
        return Response({"success": True, "message": f"Request {part_request.status.lower()}."})


class InventoryReceivingQueueAPIView(APIView):
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    def get(self, request):
        items = PurchaseItem.objects.select_related(
            "purchase__supplier",
            "part",
        ).filter(
            inventory_items__status="PENDING_RECEIPT",
        ).distinct().order_by("-purchase__invoice_date", "-id")

        paginated, page, page_size, start, end = _page_window(request)
        total_count = items.count()
        rows = []
        for item in items[start:end]:
            pending = item.inventory_items.filter(status="PENDING_RECEIPT").count()
            received = item.inventory_items.exclude(status="PENDING_RECEIPT").count()
            rows.append({
                "purchase_item_id": item.id, "invoice_number": item.purchase.invoice_number,
                "invoice_date": item.purchase.invoice_date, "supplier": item.purchase.supplier.name,
                "part_name": item.part.name, "part_code": item.part.code,
                "is_serialized": item.part.is_serialized,
                "receipt_mode": "QR" if item.part.is_serialized else "PHOTO",
                "quantity": item.quantity, "pending_count": pending, "received_count": received,
            })
        if not paginated:
            return Response({"success": True, "items": rows})
        return Response({
            "success": True,
            "items": rows,
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": end < total_count,
            "next_page": page + 1 if end < total_count else None,
        })


class InventoryReceiveAPIView(APIView):
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    @transaction.atomic
    def post(self, request):
        purchase_item_id = request.data.get("purchase_item_id")
        code = str(request.data.get("code", "")).strip()
        if not code or len(code) > 100:
            return Response({"success": False, "message": "Scan or enter a valid QR/serial code."}, status=400)
        registered = InventoryItem.objects.select_for_update().filter(
            models.Q(serial_number=code) | models.Q(barcode=code)
        ).first()
        if registered and (
            registered.purchase_item_id != int(purchase_item_id)
            or registered.status != "PENDING_RECEIPT"
        ):
            return Response({"success": False, "message": "This QR/serial code is already registered."}, status=409)
        inventory_item = registered or (
            InventoryItem.objects.select_for_update()
            .filter(
                purchase_item_id=purchase_item_id,
                status="PENDING_RECEIPT",
                serial_number__isnull=True,
                part__is_serialized=True,
            )
            .select_related("part")
            .first()
        )
        if inventory_item is not None and not inventory_item.part.is_serialized:
            return Response({"success": False, "message": "This item uses photo receipt, not QR scanning."}, status=400)
        if inventory_item is None:
            return Response({"success": False, "message": "No pending quantity remains for this purchase item."}, status=409)
        inventory_item.serial_number = code
        inventory_item.barcode = code
        inventory_item.status = "IN_STOCK"
        inventory_item.received_at = timezone.now()
        inventory_item.received_by = request.user
        inventory_item.save()
        InventoryAuditLog.objects.create(
            inventory_item=inventory_item, performed_by=request.user, action="RECEIVED",
            old_status="PENDING_RECEIPT", new_status="IN_STOCK", serial_number=code,
            remarks=f"Received against invoice {inventory_item.purchase_item.purchase.invoice_number}",
        )
        return Response({
            "success": True, "message": "Part received into stock.",
            "inventory_item_id": inventory_item.id, "part": inventory_item.part.name,
            "serial_number": code,
        }, status=201)


class InventoryPhotoReceiveAPIView(APIView):
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    @transaction.atomic
    def post(self, request):
        purchase_item_id = request.data.get("purchase_item_id")
        photo = request.FILES.get("photo")
        if not photo:
            return Response({"success": False, "message": "Item photo is required."}, status=400)
        inventory_item = (
            InventoryItem.objects.select_for_update()
            .filter(
                purchase_item_id=purchase_item_id,
                status="PENDING_RECEIPT",
                part__is_serialized=False,
            )
            .select_related("part", "purchase_item__purchase")
            .first()
        )
        if inventory_item is None:
            return Response({"success": False, "message": "No pending non-serialized quantity remains."}, status=409)
        inventory_item.receipt_photo = photo
        inventory_item.status = "IN_STOCK"
        inventory_item.received_at = timezone.now()
        inventory_item.received_by = request.user
        inventory_item.save(update_fields=["receipt_photo", "status", "received_at", "received_by"])
        InventoryAuditLog.objects.create(
            inventory_item=inventory_item, performed_by=request.user, action="RECEIVED",
            old_status="PENDING_RECEIPT", new_status="IN_STOCK", serial_number="",
            remarks=f"Photo-verified receipt against invoice {inventory_item.purchase_item.purchase.invoice_number}",
        )
        return Response({"success": True, "message": "Photo verified and item added to stock."}, status=201)


class PartRequestFulfilAPIView(APIView):
    permission_classes = [HasRequiredFeature]
    required_feature = "inventory_workflow"

    @transaction.atomic
    def post(self, request, request_id):
        part_request = get_object_or_404(
            PartRequest.objects.select_for_update().select_related("engineer", "part"), id=request_id
        )
        company_id = _company_id_for(request.user)
        if company_id and part_request.engineer.company_id != company_id:
            return Response({"success": False, "message": "This request belongs to another company."}, status=403)
        if part_request.status != "APPROVED":
            return Response({"success": False, "message": "Only approved requests can be issued."}, status=409)
        codes = request.data.get("codes") or []
        if part_request.part.is_serialized:
            if not isinstance(codes, list) or len(codes) != part_request.quantity:
                return Response({"success": False, "message": f"Scan exactly {part_request.quantity} part code(s)."}, status=400)
            clean_codes = [str(code).strip() for code in codes]
            if len(set(clean_codes)) != len(clean_codes):
                return Response({"success": False, "message": "Duplicate QR codes are not allowed."}, status=400)
            stock = list(
                InventoryItem.objects.select_for_update().filter(
                    part=part_request.part, status="IN_STOCK", serial_number__in=clean_codes,
                )
            )
        else:
            clean_codes = []
            stock = list(
                InventoryItem.objects.select_for_update().filter(
                    part=part_request.part, status="IN_STOCK", receipt_photo__isnull=False,
                ).order_by("received_at", "id")[:part_request.quantity]
            )
        if len(stock) != part_request.quantity:
            return Response({"success": False, "message": "Required verified stock is not available."}, status=409)
        for item in stock:
            EngineerBagItem.objects.create(
                engineer=part_request.engineer, inventory_item=item, status="ISSUED",
                remarks=f"Issued against part request #{part_request.id}",
            )
            item.status = "ISSUED"
            item.save(update_fields=["status"])
            InventoryAuditLog.objects.create(
                inventory_item=item, engineer=part_request.engineer, performed_by=request.user,
                action="ISSUED", old_status="IN_STOCK", new_status="ISSUED",
                serial_number=item.serial_number or "", remarks=f"Part request #{part_request.id}",
            )
        part_request.status = "FULFILLED"
        part_request.save(update_fields=["status"])
        PartRequestEvent.objects.create(
            part_request=part_request, action="FULFILLED", performed_by=request.user,
            remarks="Parts scanned and issued to engineer bag.", metadata={"codes": clean_codes},
        )
        return Response({"success": True, "message": "Request fulfilled and engineer bag updated."})
