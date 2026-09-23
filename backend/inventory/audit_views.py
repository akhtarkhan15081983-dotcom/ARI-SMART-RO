from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrManager, IsStaffOperator

from .models import InventoryItem, PartStockAudit, PartStockAuditLine, PartStockAuditScan


def _audit_payload(audit):
    lines = audit.lines.select_related("part").all()
    return {
        "id": audit.id,
        "reference": audit.reference,
        "status": audit.status,
        "started_at": audit.started_at,
        "completed_at": audit.completed_at,
        "lines": [
            {
                "id": line.id,
                "part": line.part_id,
                "part_code": line.part.code,
                "part_name": line.part.name,
                "is_serialized": line.is_serialized,
                "expected_quantity": line.expected_quantity,
                "counted_quantity": line.counted_quantity,
                "difference": line.difference,
                "verified_at": line.verified_at,
                "remarks": line.remarks,
            }
            for line in lines
        ],
    }


class PartStockAuditAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request):
        open_audit = PartStockAudit.objects.filter(status="OPEN").first()
        if open_audit:
            return Response({"detail": f"Parts audit {open_audit.reference} is already open."}, status=409)
        audit = PartStockAudit.objects.create(
            started_by=request.user,
            notes=str(request.data.get("notes") or "")[:2000],
        )
        stock = (
            InventoryItem.objects
            .filter(status="IN_STOCK")
            .values("part", "part__is_serialized")
            .annotate(quantity=Count("id"))
        )
        PartStockAuditLine.objects.bulk_create([
            PartStockAuditLine(
                audit=audit,
                part_id=row["part"],
                is_serialized=bool(row["part__is_serialized"]),
                expected_quantity=row["quantity"],
            )
            for row in stock
        ])
        return Response({"success": True, "audit": _audit_payload(audit)}, status=201)

    def get(self, request):
        audit = PartStockAudit.objects.order_by("-started_at").first()
        return Response({"audit": _audit_payload(audit) if audit else None})


class PartStockAuditScanAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request, audit_id):
        audit = PartStockAudit.objects.select_for_update().filter(pk=audit_id, status="OPEN").first()
        if audit is None:
            return Response({"detail": "Open parts audit not found."}, status=404)
        code = str(request.data.get("code") or "").strip()
        item = (
            InventoryItem.objects
            .select_related("part")
            .filter(Q(serial_number=code) | Q(barcode=code), status="IN_STOCK")
            .first()
        )
        if item is None:
            return Response({"detail": "In-stock serialized part was not found for this code."}, status=404)
        if not item.part.is_serialized:
            return Response({"detail": "This is a non-scan part. Enter its physical quantity instead."}, status=409)
        line = audit.lines.select_for_update().filter(part=item.part).first()
        if line is None:
            return Response({"detail": "This part was not expected in stock when the audit started."}, status=409)
        _, created = PartStockAuditScan.objects.get_or_create(
            audit_line=line,
            inventory_item=item,
            defaults={"scanned_by": request.user},
        )
        if not created:
            return Response({"detail": "This physical part was already scanned in this audit."}, status=409)
        line.counted_quantity = line.scans.count()
        line.verified_by = request.user
        line.verified_at = timezone.now()
        line.save(update_fields=["counted_quantity", "verified_by", "verified_at"])
        return Response({
            "success": True,
            "part_code": item.part.code,
            "expected_quantity": line.expected_quantity,
            "counted_quantity": line.counted_quantity,
            "difference": line.difference,
        })


class PartStockAuditCountAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request, audit_id, line_id):
        line = (
            PartStockAuditLine.objects
            .select_for_update()
            .select_related("audit", "part")
            .filter(pk=line_id, audit_id=audit_id, audit__status="OPEN")
            .first()
        )
        if line is None:
            return Response({"detail": "Open audit line not found."}, status=404)
        if line.is_serialized:
            return Response({"detail": "Serialized parts must be verified by scanning each physical unit."}, status=409)
        try:
            count = int(request.data.get("counted_quantity"))
            if count < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"detail": "Enter a valid physical quantity."}, status=400)
        line.counted_quantity = count
        line.verified_by = request.user
        line.verified_at = timezone.now()
        line.remarks = str(request.data.get("remarks") or "")[:300]
        line.save(update_fields=["counted_quantity", "verified_by", "verified_at", "remarks"])
        return Response({
            "success": True,
            "part_code": line.part.code,
            "expected_quantity": line.expected_quantity,
            "counted_quantity": line.counted_quantity,
            "difference": line.difference,
        })


class PartStockAuditCompleteAPIView(APIView):
    permission_classes = [IsAdminOrManager]

    @transaction.atomic
    def post(self, request, audit_id):
        audit = PartStockAudit.objects.select_for_update().filter(pk=audit_id, status="OPEN").first()
        if audit is None:
            return Response({"detail": "Open parts audit not found."}, status=404)
        unverified = audit.lines.filter(verified_at__isnull=True).count()
        if unverified:
            return Response({"detail": f"Verify all part lines before completing the audit. {unverified} line(s) remain."}, status=409)
        audit.status = "COMPLETED"
        audit.completed_at = timezone.now()
        audit.save(update_fields=["status", "completed_at"])
        differences = [
            {
                "part_code": line.part.code,
                "part_name": line.part.name,
                "expected": line.expected_quantity,
                "counted": line.counted_quantity,
                "difference": line.difference,
            }
            for line in audit.lines.select_related("part")
            if line.difference != 0
        ]
        return Response({
            "success": True,
            "reference": audit.reference,
            "difference_count": len(differences),
            "differences": differences,
        })
