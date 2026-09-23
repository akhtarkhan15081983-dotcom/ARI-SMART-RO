from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrManager, IsOperationsUser, IsStaffOperator
from customers.models import Customer, PublicCustomerRequest
from products.models import ROModel

from .models import (
    ROAsset,
    ROAssetComponent,
    ROAssetMovement,
    ROStockAudit,
    ROStockAuditItem,
)
from .serializers import ROAssetMovementSerializer, ROAssetSerializer


def _clean_serial(value):
    return str(value or "").strip()[:100]


def _movement(*, asset, action, user, customer=None, request_row=None, old_status="", remarks=""):
    return ROAssetMovement.objects.create(
        asset=asset,
        action=action,
        customer=customer,
        request_id=getattr(request_row, "id", None),
        request_number=str(getattr(request_row, "request_number", "") or ""),
        from_status=old_status,
        to_status=asset.status,
        performed_by=user,
        remarks=str(remarks or "")[:1000],
    )


def _sync_model_stock(ro_model):
    assets = ROAsset.objects.filter(ro_model=ro_model, status="WAREHOUSE", is_active=True).prefetch_related("components")
    count = sum(1 for asset in assets if asset.release_ready)
    if ro_model.stock_quantity != count:
        ro_model.stock_quantity = count
        ro_model.save(update_fields=["stock_quantity"])
    return count


def _release_blockers(asset):
    blockers = []
    active_components = asset.components.filter(status="ACTIVE")
    if asset.qc_status != "PASSED":
        blockers.append("QC must be passed.")
    if not active_components.exists():
        blockers.append("RO model BOM/components are not configured.")
    pending = active_components.filter(scan_status="PENDING").select_related("part")
    if pending.exists():
        names = ", ".join(p.part.name for p in pending[:5])
        blockers.append(f"Serialized component verification pending: {names}.")
    if asset.reservation_active:
        blockers.append("RO is reserved for another customer.")
    return blockers


class ROAssetListAPIView(generics.ListAPIView):
    serializer_class = ROAssetSerializer
    permission_classes = [IsOperationsUser]

    def get_queryset(self):
        queryset = ROAsset.objects.select_related(
            "ro_model", "current_customer", "reserved_for_customer"
        ).prefetch_related("components__part")
        status_value = str(self.request.GET.get("status", "WAREHOUSE") or "WAREHOUSE").strip().upper()
        if status_value != "ALL":
            queryset = queryset.filter(status=status_value)
        keyword = str(self.request.GET.get("q", "") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(asset_id__icontains=keyword)
                | Q(serial_number__icontains=keyword)
                | Q(ro_model__model_name__icontains=keyword)
                | Q(current_customer__name__icontains=keyword)
            )
        return queryset.filter(is_active=True).order_by("asset_id")


class ROAssetWorkflowSummaryAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        by_status = {
            row["status"]: row["count"]
            for row in ROAsset.objects.filter(is_active=True).values("status").annotate(count=Count("id"))
        }
        warehouse = list(
            ROAsset.objects.filter(is_active=True, status="WAREHOUSE").prefetch_related("components")
        )
        return Response({
            "summary": {
                "total": sum(by_status.values()),
                "warehouse": by_status.get("WAREHOUSE", 0),
                "release_ready": sum(1 for asset in warehouse if asset.release_ready),
                "qc_pending": sum(1 for asset in warehouse if asset.qc_status == "PENDING"),
                "bom_pending": sum(1 for asset in warehouse if not asset.bom_verified),
                "assigned": by_status.get("ASSIGNED", 0),
                "installed": by_status.get("INSTALLED", 0),
                "returned": by_status.get("RETURNED", 0),
                "repair": by_status.get("REPAIR", 0),
                "scrap": by_status.get("SCRAP", 0),
                "sale_allocated": ROAsset.objects.filter(is_active=True, deployment_type="SALE").count(),
                "rent_allocated": ROAsset.objects.filter(is_active=True, deployment_type="RENT").count(),
            }
        })


class ROAssetReceiveAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        try:
            model_id = int(request.data.get("ro_model"))
        except (TypeError, ValueError):
            return Response({"detail": "Select a valid RO model."}, status=400)
        ro_model = ROModel.objects.select_for_update().filter(pk=model_id, is_active=True).first()
        if ro_model is None:
            return Response({"detail": "RO model not found or inactive."}, status=404)

        raw_serials = request.data.get("serial_numbers")
        if isinstance(raw_serials, str):
            raw_serials = raw_serials.replace(",", "\n").splitlines()
        if not isinstance(raw_serials, list):
            return Response({"detail": "Provide serial_numbers as a list or one-per-line text."}, status=400)
        serials = [_clean_serial(v) for v in raw_serials if _clean_serial(v)]
        if not serials:
            return Response({"detail": "At least one RO serial number is required."}, status=400)
        if len(serials) != len(set(serials)):
            return Response({"detail": "Duplicate serial numbers were entered in this receipt."}, status=400)
        existing = set(ROAsset.objects.filter(serial_number__in=serials).values_list("serial_number", flat=True))
        if existing:
            return Response({"detail": f"Already registered serial(s): {', '.join(sorted(existing)[:8])}"}, status=409)

        invoice = str(request.data.get("purchase_invoice", "") or "").strip()[:100]
        purchase_date = request.data.get("purchase_date") or timezone.localdate()
        try:
            purchase_price = Decimal(str(request.data.get("purchase_price", 0) or 0))
            if purchase_price < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response({"detail": "Enter a valid purchase price."}, status=400)

        assets = []
        for serial in serials:
            asset = ROAsset.objects.create(
                ro_model=ro_model,
                serial_number=serial,
                qr_code=f"ARI-RO:{serial}",
                status="WAREHOUSE",
                qc_status="PENDING",
                purchase_date=purchase_date,
                purchase_invoice=invoice,
                purchase_price=purchase_price,
            )
            _movement(asset=asset, action="RECEIVED", user=request.user, remarks=f"Received into warehouse. Invoice {invoice}".strip())
            assets.append(asset)

        stock = _sync_model_stock(ro_model)
        return Response({
            "success": True,
            "received": len(assets),
            "stock_quantity": stock,
            "message": "RO units received. QC and BOM verification are required before sale/rent.",
            "assets": ROAssetSerializer(assets, many=True).data,
        }, status=status.HTTP_201_CREATED)


class ROAssetQCAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = ROAsset.objects.select_for_update().select_related("ro_model").filter(pk=asset_id, is_active=True).first()
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        action = str(request.data.get("result") or "").upper()
        if action not in {"PASS", "FAIL"}:
            return Response({"detail": "QC result must be PASS or FAIL."}, status=400)
        checklist = request.data.get("checklist") or {}
        if action == "PASS":
            required = ["pump_run", "leakage_test", "smps", "membrane", "body_damage"]
            missing = [key for key in required if checklist.get(key) is not True]
            if missing:
                return Response({"detail": f"QC checklist incomplete: {', '.join(missing)}."}, status=409)
        asset.qc_status = "PASSED" if action == "PASS" else "FAILED"
        asset.qc_checked_at = timezone.now()
        asset.qc_checked_by = request.user
        asset.qc_notes = str(request.data.get("notes") or "")[:2000]
        if request.data.get("cleaned") is True:
            asset.cleaned_at = timezone.now()
        if request.data.get("sanitized") is True:
            asset.sanitized_at = timezone.now()
        asset.save(update_fields=["qc_status", "qc_checked_at", "qc_checked_by", "qc_notes", "cleaned_at", "sanitized_at"])
        _movement(asset=asset, action="QC_PASSED" if action == "PASS" else "QC_FAILED", user=request.user, remarks=asset.qc_notes)
        stock = _sync_model_stock(asset.ro_model)
        return Response({"success": True, "asset": ROAssetSerializer(asset).data, "stock_quantity": stock, "release_blockers": _release_blockers(asset)})


class ROAssetReserveAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = ROAsset.objects.select_for_update().filter(pk=asset_id, status="WAREHOUSE", is_active=True).first()
        if asset is None:
            return Response({"detail": "Available warehouse RO not found."}, status=404)
        if not asset.release_ready and not asset.reservation_active:
            blockers = _release_blockers(asset)
            return Response({"detail": "RO is not release-ready.", "blockers": blockers}, status=409)
        try:
            customer_id = int(request.data.get("customer_id"))
            minutes = max(15, min(int(request.data.get("minutes") or 1440), 10080))
        except (TypeError, ValueError):
            return Response({"detail": "Valid customer and reservation duration are required."}, status=400)
        customer = Customer.objects.filter(pk=customer_id, is_active=True).first()
        if customer is None:
            return Response({"detail": "Active customer not found."}, status=404)
        if asset.reservation_active and asset.reserved_for_customer_id != customer.id:
            return Response({"detail": "RO is already reserved for another customer."}, status=409)
        asset.reserved_for_customer = customer
        asset.reserved_at = timezone.now()
        asset.reservation_expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
        asset.save(update_fields=["reserved_for_customer", "reserved_at", "reservation_expires_at"])
        _movement(asset=asset, action="RESERVED", user=request.user, customer=customer, remarks=f"Reserved for {minutes} minutes")
        _sync_model_stock(asset.ro_model)
        return Response({"success": True, "asset": ROAssetSerializer(asset).data})

    @transaction.atomic
    def delete(self, request, asset_id):
        asset = ROAsset.objects.select_for_update().select_related("ro_model").filter(pk=asset_id, is_active=True).first()
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        customer = asset.reserved_for_customer
        asset.reserved_for_customer = None
        asset.reserved_at = None
        asset.reservation_expires_at = None
        asset.save(update_fields=["reserved_for_customer", "reserved_at", "reservation_expires_at"])
        _movement(asset=asset, action="RESERVATION_RELEASED", user=request.user, customer=customer)
        _sync_model_stock(asset.ro_model)
        return Response({"success": True})


class ROAssetAllocateAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = ROAsset.objects.select_for_update().select_related("ro_model", "current_customer", "reserved_for_customer").filter(pk=asset_id, is_active=True).first()
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        if asset.status != "WAREHOUSE" or asset.current_customer_id is not None:
            return Response({"detail": "This RO is not available in warehouse stock."}, status=409)
        mode = str(request.data.get("deployment_type", "") or "").strip().upper()
        if mode not in {"SALE", "RENT"}:
            return Response({"detail": "deployment_type must be SALE or RENT."}, status=400)
        try:
            customer_id = int(request.data.get("customer_id"))
        except (TypeError, ValueError):
            return Response({"detail": "Select a valid customer."}, status=400)
        customer = Customer.objects.select_for_update().filter(pk=customer_id, is_active=True).first()
        if customer is None:
            return Response({"detail": "Active customer not found."}, status=404)
        if asset.reservation_active and asset.reserved_for_customer_id != customer.id:
            return Response({"detail": "This RO is reserved for another customer."}, status=409)
        blockers = [b for b in _release_blockers(asset) if not b.startswith("RO is reserved")]
        if blockers:
            return Response({"detail": "RO is not ready for sale/rent.", "blockers": blockers}, status=409)

        request_row = None
        raw_request_id = request.data.get("request_id")
        if raw_request_id not in (None, ""):
            try:
                request_row = PublicCustomerRequest.objects.select_for_update().get(pk=int(raw_request_id))
            except (ValueError, PublicCustomerRequest.DoesNotExist):
                return Response({"detail": "Customer purchase/rental request not found."}, status=404)
            expected = "PURCHASE" if mode == "SALE" else "RENTAL"
            if request_row.request_type != expected:
                return Response({"detail": f"Selected request is not a {expected.lower()} request."}, status=409)
            if request_row.product_id and request_row.product_id != asset.ro_model_id:
                return Response({"detail": "Requested RO model does not match this physical RO."}, status=409)
            request_row.existing_customer = customer
            request_row.status = "CONFIRMED"
            request_row.save(update_fields=["existing_customer", "status", "updated_at"])

        old_status = asset.status
        asset.status = "ASSIGNED"
        asset.deployment_type = mode
        asset.current_customer = customer
        asset.assigned_at = timezone.now()
        asset.reserved_for_customer = None
        asset.reserved_at = None
        asset.reservation_expires_at = None
        asset.save(update_fields=["status", "deployment_type", "current_customer", "assigned_at", "reserved_for_customer", "reserved_at", "reservation_expires_at"])

        customer.ro_model = asset.ro_model.model_name
        customer.ownership_type = "PURCHASE" if mode == "SALE" else "RENTAL"
        if mode == "RENT":
            customer.monthly_rent = asset.ro_model.monthly_rent
            customer.security_deposit = asset.ro_model.security_deposit
            customer.installation_charge = asset.ro_model.installation_charge
        customer.save(update_fields=["ro_model", "ownership_type", "monthly_rent", "security_deposit", "installation_charge"])
        stock = _sync_model_stock(asset.ro_model)
        _movement(asset=asset, action="SALE_ALLOCATED" if mode == "SALE" else "RENT_ALLOCATED", user=request.user, customer=customer, request_row=request_row, old_status=old_status, remarks=request.data.get("remarks", ""))
        return Response({"success": True, "message": f"RO {asset.asset_id} allocated for {mode.lower()}.", "asset": ROAssetSerializer(asset).data, "stock_quantity": stock})


class ROAssetReturnAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = ROAsset.objects.select_for_update().select_related("ro_model", "current_customer").filter(pk=asset_id, is_active=True).first()
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        if asset.deployment_type != "RENT" or asset.status not in {"ASSIGNED", "INSTALLED", "SERVICE", "REPAIR"}:
            return Response({"detail": "Only an active rental RO can be returned."}, status=409)
        old_status = asset.status
        customer = asset.current_customer
        asset.status = "RETURNED"
        asset.qc_status = "PENDING"
        asset.cleaned_at = None
        asset.sanitized_at = None
        asset.save(update_fields=["status", "qc_status", "cleaned_at", "sanitized_at"])
        _movement(asset=asset, action="RENT_RETURNED", user=request.user, customer=customer, old_status=old_status, remarks=request.data.get("remarks", ""))
        return Response({"success": True, "asset": ROAssetSerializer(asset).data, "message": "Rental RO returned. QC, cleaning and sanitization are required before restock."})


class ROAssetRestockAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, asset_id):
        asset = ROAsset.objects.select_for_update().select_related("ro_model", "current_customer").filter(pk=asset_id, is_active=True).first()
        if asset is None:
            return Response({"detail": "RO asset not found."}, status=404)
        if asset.status not in {"RETURNED", "REFURBISHED"}:
            return Response({"detail": "Only returned/refurbished RO can be restocked."}, status=409)
        if asset.qc_status != "PASSED" or asset.cleaned_at is None or asset.sanitized_at is None:
            return Response({"detail": "Return QC, cleaning and sanitization must be completed before restock."}, status=409)
        if not asset.bom_verified:
            return Response({"detail": "Component/BOM verification is incomplete."}, status=409)
        old_status = asset.status
        customer = asset.current_customer
        asset.status = "WAREHOUSE"
        asset.deployment_type = ""
        asset.current_customer = None
        asset.assigned_at = None
        asset.save(update_fields=["status", "deployment_type", "current_customer", "assigned_at"])
        stock = _sync_model_stock(asset.ro_model)
        _movement(asset=asset, action="RESTOCKED", user=request.user, customer=customer, old_status=old_status, remarks=request.data.get("remarks", ""))
        return Response({"success": True, "asset": ROAssetSerializer(asset).data, "stock_quantity": stock})


class ROAssetMovementListAPIView(generics.ListAPIView):
    serializer_class = ROAssetMovementSerializer
    permission_classes = [IsStaffOperator]

    def get_queryset(self):
        queryset = ROAssetMovement.objects.select_related("asset__ro_model", "customer", "performed_by")
        raw_asset = self.request.GET.get("asset_id")
        if str(raw_asset or "").isdigit():
            queryset = queryset.filter(asset_id=int(raw_asset))
        return queryset[:500]


class ROStockAuditAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request):
        open_audit = ROStockAudit.objects.filter(status="OPEN").first()
        if open_audit:
            return Response({"detail": f"Stock audit {open_audit.reference} is already open."}, status=409)
        audit = ROStockAudit.objects.create(started_by=request.user, notes=str(request.data.get("notes") or ""))
        items = [
            ROStockAuditItem(audit=audit, asset=asset, expected_status=asset.status)
            for asset in ROAsset.objects.filter(is_active=True, status="WAREHOUSE")
        ]
        ROStockAuditItem.objects.bulk_create(items, batch_size=500)
        return Response({"success": True, "audit_id": audit.id, "reference": audit.reference, "expected": len(items)}, status=201)

    def get(self, request):
        audit = ROStockAudit.objects.order_by("-started_at").first()
        if audit is None:
            return Response({"audit": None})
        items = audit.items.select_related("asset__ro_model")
        return Response({"audit": {"id": audit.id, "reference": audit.reference, "status": audit.status, "expected": items.count(), "found": items.filter(physically_found=True).count(), "missing": items.filter(physically_found=False).count(), "started_at": audit.started_at}})


class ROStockAuditScanAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request, audit_id):
        audit = ROStockAudit.objects.select_for_update().filter(pk=audit_id, status="OPEN").first()
        if audit is None:
            return Response({"detail": "Open stock audit not found."}, status=404)
        code = str(request.data.get("code") or "").strip()
        asset = ROAsset.objects.filter(Q(serial_number=code) | Q(asset_id=code) | Q(qr_code=code), is_active=True).first()
        if asset is None:
            return Response({"detail": "RO serial/QR not found."}, status=404)
        item = audit.items.filter(asset=asset).first()
        if item is None:
            return Response({"detail": "This RO was not expected in warehouse at audit start.", "asset_id": asset.asset_id, "current_status": asset.status}, status=409)
        item.physically_found = True
        item.scanned_at = timezone.now()
        item.scanned_by = request.user
        item.save(update_fields=["physically_found", "scanned_at", "scanned_by"])
        return Response({"success": True, "asset_id": asset.asset_id, "serial_number": asset.serial_number})


class ROStockAuditCompleteAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, audit_id):
        audit = ROStockAudit.objects.select_for_update().filter(pk=audit_id, status="OPEN").first()
        if audit is None:
            return Response({"detail": "Open stock audit not found."}, status=404)
        missing = audit.items.filter(physically_found=False).select_related("asset")
        audit.status = "COMPLETED"
        audit.completed_at = timezone.now()
        audit.save(update_fields=["status", "completed_at"])
        return Response({"success": True, "reference": audit.reference, "missing_count": missing.count(), "missing_assets": [row.asset.asset_id for row in missing[:100]]})
