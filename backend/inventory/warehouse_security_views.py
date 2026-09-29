from io import BytesIO
from secrets import token_hex

import openpyxl
import qrcode
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffOperator
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.access import request_company

from .models import InventoryAuditLog, InventoryItem, PartRequest
from .reports import _sheet


def _company_id(request):
    company = request_company(request)
    return company.id if company is not None else None


def _scoped_purchase_items(request):
    return PurchaseItem.objects.filter(company_id=_company_id(request))


def _scoped_inventory(request):
    return InventoryItem.objects.filter(company_id=_company_id(request))


class TenantScopedInventoryReceivingQueueAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        items = (
            _scoped_purchase_items(request)
            .select_related("purchase__supplier", "part")
            .order_by("-purchase__invoice_date", "-id")
        )
        rows = []
        for item in items[:250]:
            pending = item.inventory_items.filter(
                company_id=_company_id(request), status="PENDING_RECEIPT"
            ).count()
            received = item.inventory_items.filter(company_id=_company_id(request)).exclude(
                status="PENDING_RECEIPT"
            ).count()
            if pending:
                rows.append({
                    "purchase_item_id": item.id,
                    "invoice_number": item.purchase.invoice_number,
                    "invoice_date": item.purchase.invoice_date,
                    "supplier": item.purchase.supplier.name,
                    "part_name": item.part.name,
                    "part_code": item.part.code,
                    "is_serialized": item.part.is_serialized,
                    "receipt_mode": "QR" if item.part.is_serialized else "PHOTO",
                    "quantity": item.quantity,
                    "pending_count": pending,
                    "received_count": received,
                })
        return Response({"success": True, "items": rows})


class TenantScopedInventoryReceiveAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        company_id = _company_id(request)
        purchase_item_id = request.data.get("purchase_item_id")
        code = str(request.data.get("code", "")).strip()
        if not code or len(code) > 100:
            return Response({"success": False, "message": "Scan or enter a valid QR/serial code."}, status=400)
        purchase_item = (
            _scoped_purchase_items(request)
            .select_related("purchase", "part")
            .filter(pk=purchase_item_id)
            .first()
        )
        if purchase_item is None:
            return Response({"success": False, "message": "Purchase item not found in this workspace."}, status=404)
        if not purchase_item.part.is_serialized:
            return Response({"success": False, "message": "This item uses photo receipt, not QR scanning."}, status=400)
        if InventoryItem.objects.exclude(company_id=company_id).filter(
            serial_number=code
        ).exists():
            return Response({"success": False, "message": "This QR/serial code is unavailable."}, status=409)

        inventory_item = (
            _scoped_inventory(request)
            .select_for_update()
            .filter(
                purchase_item=purchase_item,
                status="PENDING_RECEIPT",
            )
            .filter(serial_number__in=[None, ""])
            .select_related("part", "purchase_item__purchase")
            .first()
        )
        if inventory_item is None:
            registered = (
                _scoped_inventory(request)
                .select_for_update()
                .filter(
                    purchase_item=purchase_item,
                    status="PENDING_RECEIPT",
                    serial_number=code,
                )
                .first()
            )
            inventory_item = registered
        if inventory_item is None:
            return Response({"success": False, "message": "No pending quantity remains for this purchase item."}, status=409)

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
        return Response({
            "success": True,
            "message": "Part received into stock.",
            "inventory_item_id": inventory_item.id,
            "part": inventory_item.part.name,
            "serial_number": code,
        }, status=201)


class TenantScopedInventoryPhotoReceiveAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        company_id = _company_id(request)
        purchase_item_id = request.data.get("purchase_item_id")
        photo = request.FILES.get("photo")
        if not photo:
            return Response({"success": False, "message": "Item photo is required."}, status=400)
        purchase_item = _scoped_purchase_items(request).filter(pk=purchase_item_id).first()
        if purchase_item is None:
            return Response({"success": False, "message": "Purchase item not found in this workspace."}, status=404)
        inventory_item = (
            _scoped_inventory(request)
            .select_for_update()
            .filter(
                purchase_item=purchase_item,
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
            company_id=company_id,
            inventory_item=inventory_item,
            performed_by=request.user,
            action="RECEIVED",
            old_status="PENDING_RECEIPT",
            new_status="IN_STOCK",
            serial_number="",
            remarks=f"Photo-verified receipt against invoice {inventory_item.purchase_item.purchase.invoice_number}",
        )
        return Response({"success": True, "message": "Photo verified and item added to stock."}, status=201)


class TenantScopedInventoryCodeGenerationAPIView(APIView):
    permission_classes = [IsStaffOperator]

    @transaction.atomic
    def post(self, request):
        company_id = _company_id(request)
        purchase_item_id = request.data.get("purchase_item_id")
        purchase_id = request.data.get("purchase_id")
        scope = _scoped_inventory(request).select_for_update().filter(
            status="PENDING_RECEIPT",
            serial_number__isnull=True,
            part__is_serialized=True,
        ).select_related("part", "purchase_item")
        if purchase_item_id:
            if not _scoped_purchase_items(request).filter(pk=purchase_item_id).exists():
                return Response({"success": False, "message": "Purchase item not found in this workspace."}, status=404)
            scope = scope.filter(purchase_item_id=purchase_item_id)
        elif purchase_id:
            if not Purchase.objects.filter(pk=purchase_id, company_id=company_id).exists():
                return Response({"success": False, "message": "Purchase not found in this workspace."}, status=404)
            scope = scope.filter(purchase_item__purchase_id=purchase_id)
        else:
            return Response({"success": False, "message": "Purchase or purchase item is required."}, status=400)

        items = list(scope.order_by("purchase_item_id", "id"))
        codes = []
        for item in items:
            while True:
                code = f"ARI-{item.part.code}-{token_hex(5).upper()}"
                if not InventoryItem.objects.filter(serial_number=code).exists():
                    break
            item.serial_number = code
            item.barcode = code
            item.save(update_fields=["serial_number", "barcode"])
            InventoryAuditLog.objects.create(
                company_id=company_id,
                inventory_item=item,
                performed_by=request.user,
                action="STATUS_CHANGE",
                old_status="PENDING_RECEIPT",
                new_status="PENDING_RECEIPT",
                serial_number=code,
                remarks="Internal QR label generated before receipt.",
            )
            codes.append(code)
        return Response({"success": True, "generated": len(codes), "codes": codes})


class TenantScopedInventoryQrLabelsPdfAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        queryset = (
            _scoped_inventory(request)
            .filter(part__is_serialized=True)
            .exclude(serial_number__isnull=True)
            .exclude(serial_number="")
            .select_related("part", "purchase_item__purchase")
        )
        purchase_item_id = request.query_params.get("purchase_item_id")
        purchase_id = request.query_params.get("purchase_id")
        if purchase_item_id:
            queryset = queryset.filter(purchase_item_id=purchase_item_id)
        if purchase_id:
            queryset = queryset.filter(purchase_item__purchase_id=purchase_id)
        items = list(queryset.order_by("part__code", "id")[:1000])
        if not items:
            return Response({"success": False, "message": "No QR labels are available."}, status=404)

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        page_width, page_height = A4
        cols, rows = 3, 8
        card_width, card_height = page_width / cols, page_height / rows
        for index, item in enumerate(items):
            slot = index % (cols * rows)
            if index and slot == 0:
                pdf.showPage()
            col, row = slot % cols, slot // cols
            x, y = col * card_width, page_height - (row + 1) * card_height
            pdf.roundRect(x + 3 * mm, y + 3 * mm, card_width - 6 * mm, card_height - 6 * mm, 2 * mm)
            qr = qrcode.make(item.serial_number)
            image_buffer = BytesIO()
            qr.save(image_buffer, format="PNG")
            image_buffer.seek(0)
            pdf.drawImage(ImageReader(image_buffer), x + 6 * mm, y + 6 * mm, 22 * mm, 22 * mm)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(x + 30 * mm, y + 25 * mm, item.part.code[:22])
            pdf.setFont("Helvetica", 6.5)
            pdf.drawString(x + 30 * mm, y + 19 * mm, item.part.name[:28])
            pdf.drawString(x + 30 * mm, y + 13 * mm, item.serial_number[:28])
            pdf.drawString(x + 30 * mm, y + 7 * mm, f"INV: {item.purchase_item.purchase.invoice_number}"[:30])
        pdf.save()
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="ARI_Inventory_QR_Labels.pdf"'
        return response


class TenantScopedInventorySummaryAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        inventory = _scoped_inventory(request)
        by_status = {
            row["status"]: row["count"]
            for row in inventory.values("status").annotate(count=Count("id"))
        }
        requests = PartRequest.objects.filter(company_id=_company_id(request))
        return Response({
            "success": True,
            "summary": {
                "total_units": inventory.count(),
                "pending_receipt": by_status.get("PENDING_RECEIPT", 0),
                "in_stock": by_status.get("IN_STOCK", 0),
                "issued": by_status.get("ISSUED", 0),
                "installed": by_status.get("INSTALLED", 0),
                "scrap": by_status.get("SCRAP", 0),
                "pending_requests": requests.filter(status="PENDING").count(),
                "approved_requests": requests.filter(status="APPROVED").count(),
            },
        })


class TenantScopedInventoryExcelReportAPIView(APIView):
    permission_classes = [IsStaffOperator]

    def get(self, request):
        company_id = _company_id(request)
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)

        inventory = _scoped_inventory(request).select_related(
            "part", "purchase_item__purchase__supplier", "received_by"
        )
        purchases = PurchaseItem.objects.filter(company_id=company_id).select_related(
            "purchase__supplier", "purchase__verified_by", "part"
        )
        requests = PartRequest.objects.filter(company_id=company_id).select_related(
            "engineer__user", "part", "reviewed_by"
        )
        audit = InventoryAuditLog.objects.filter(company_id=company_id).select_related(
            "inventory_item__part", "engineer__user", "performed_by"
        )
        summary = inventory.values("status").annotate(units=Count("id")).order_by("status")

        _sheet(workbook, "Executive Summary", ["Metric", "Value"], [
            ("Generated By", request.user.get_full_name() or request.user.phone),
            ("Total Suppliers", Supplier.objects.filter(company_id=company_id).count()),
            ("Total Purchases", Purchase.objects.filter(company_id=company_id).count()),
            ("Inventory Units", inventory.count()),
            ("Stock Value", float(purchases.aggregate(value=Sum("purchase_price"))["value"] or 0)),
            *[(f"Status: {row['status']}", row["units"]) for row in summary],
        ])
        _sheet(workbook, "Stock Ledger", ["ID", "Part Code", "Part", "Serial-QR", "Status", "Invoice", "Supplier"], [
            (item.id, item.part.code, item.part.name, item.serial_number or "", item.status,
             item.purchase_item.purchase.invoice_number, item.purchase_item.purchase.supplier.name)
            for item in inventory
        ])
        _sheet(workbook, "Purchases", ["Invoice", "Date", "Supplier", "Part Code", "Part", "Quantity", "Unit Price"], [
            (item.purchase.invoice_number, item.purchase.invoice_date, item.purchase.supplier.name,
             item.part.code, item.part.name, item.quantity, float(item.purchase_price))
            for item in purchases
        ])
        _sheet(workbook, "Part Requests", ["Request", "Employee", "Part", "Qty", "Status"], [
            (row.id, row.engineer.user.get_full_name(), row.part.name, row.quantity, row.status)
            for row in requests
        ])
        _sheet(workbook, "Audit Trail", ["Time", "Action", "Part", "Serial", "Engineer", "Performed By"], [
            (row.created_at.replace(tzinfo=None), row.action, row.inventory_item.part.name, row.serial_number,
             row.engineer.user.get_full_name() if row.engineer else "",
             (row.performed_by.get_full_name() or row.performed_by.phone) if row.performed_by else "")
            for row in audit
        ])
        output = BytesIO()
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="ARI_Professional_Inventory_Report.xlsx"'
        return response
