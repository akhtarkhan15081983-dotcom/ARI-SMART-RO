import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaffOperator
from partmaster.models import PartMaster

from .models import Purchase, Supplier
from .serializers import PurchaseSerializer


def _clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _date_from_text(text):
    patterns = (
        r"(?:invoice\s*date|dated?|date)\s*[:#-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        value = match.group(1).replace("-", "/")
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    return date.today()


def _invoice_number(text):
    for pattern in (
        r"(?:invoice|inv|bill)\s*(?:no|number|#)?\s*[:#-]\s*([A-Z0-9][A-Z0-9/-]{2,30})",
        r"(?:invoice|inv)\s+(?:no|number)\s+([A-Z0-9][A-Z0-9/-]{2,30})",
    ):
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).upper()
    return ""


def _supplier_match(text):
    normalized = text.lower()
    suppliers = list(Supplier.objects.filter(is_active=True).order_by("name"))
    for supplier in suppliers:
        candidates = [supplier.name, supplier.gst_number, supplier.phone]
        if any(value and value.lower() in normalized for value in candidates):
            return supplier
    return None


def _part_lines(text):
    lines = [_clean(line) for line in text.splitlines() if _clean(line)]
    results, used = [], set()
    parts = PartMaster.objects.all().order_by("code")
    for part in parts:
        keys = [part.code.lower(), part.name.lower()]
        line = next((row for row in lines if any(key and key in row.lower() for key in keys)), None)
        if not line or part.id in used:
            continue
        numbers = re.findall(r"(?<![A-Za-z])\d+(?:\.\d{1,2})?", line.replace(",", ""))
        quantity = 1
        price = Decimal("0")
        if numbers:
            try:
                quantity = max(1, int(Decimal(numbers[0])))
                if len(numbers) > 1:
                    price = Decimal(numbers[-1])
            except (InvalidOperation, ValueError):
                pass
        results.append({
            "part": part.id, "part_code": part.code, "part_name": part.name,
            "quantity": quantity, "purchase_price": str(price), "source_line": line,
        })
        used.add(part.id)
    return results


def analyze(text):
    text = str(text or "")[:50000]
    supplier = _supplier_match(text)
    invoice = _invoice_number(text)
    invoice_date = _date_from_text(text)
    items = _part_lines(text)
    checks = [bool(supplier), bool(invoice), bool(items), invoice_date != date.today()]
    confidence = round(sum(checks) / len(checks) * 100, 2)
    duplicate = bool(invoice and Purchase.objects.filter(
        invoice_number__iexact=invoice,
        **({"supplier": supplier} if supplier else {}),
    ).exists())
    warnings = []
    if not supplier: warnings.append("Supplier could not be matched; please select it.")
    if not invoice: warnings.append("Invoice number needs manual confirmation.")
    if not items: warnings.append("No catalog parts were matched; add invoice lines manually.")
    if duplicate: warnings.append("Possible duplicate invoice detected. It cannot be posted twice.")
    return {
        "supplier": supplier.id if supplier else None,
        "supplier_name": supplier.name if supplier else "",
        "invoice_number": invoice,
        "invoice_date": invoice_date.isoformat(),
        "items": items,
        "confidence": confidence,
        "duplicate": duplicate,
        "warnings": warnings,
    }


class InvoiceAnalyzeAPIView(APIView):
    permission_classes = [IsStaffOperator]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        text = request.data.get("ocr_text", "")
        if len(_clean(text)) < 10:
            return Response({"message": "Invoice text could not be read. Retake a clear, flat photo."}, status=400)
        return Response({"success": True, "draft": analyze(text)})


class InvoiceConfirmAPIView(APIView):
    permission_classes = [IsStaffOperator]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        try:
            payload = json.loads(request.data.get("payload", "{}"))
        except json.JSONDecodeError:
            return Response({"message": "Invoice verification data is invalid."}, status=400)
        supplier_id = payload.get("supplier")
        invoice_number = _clean(payload.get("invoice_number"))
        if not supplier_id or not invoice_number:
            return Response({"message": "Supplier and invoice number are required."}, status=400)
        if Purchase.objects.filter(supplier_id=supplier_id, invoice_number__iexact=invoice_number).exists():
            return Response({"message": "This supplier invoice already exists. Duplicate posting blocked."}, status=409)
        serializer = PurchaseSerializer(data={
            "supplier": supplier_id,
            "invoice_number": invoice_number,
            "invoice_date": payload.get("invoice_date"),
            "remarks": _clean(payload.get("remarks")),
            "items": payload.get("items", []),
        })
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()
        purchase.invoice_image = request.FILES.get("invoice_image")
        purchase.entry_source = "INVOICE_OCR"
        purchase.ocr_text = str(request.data.get("ocr_text", ""))[:50000]
        try:
            purchase.ocr_confidence = Decimal(str(payload.get("ocr_confidence", 0)))
        except InvalidOperation:
            purchase.ocr_confidence = Decimal("0")
        purchase.verified_by = request.user
        purchase.verified_at = timezone.now()
        purchase.save(update_fields=(
            "invoice_image", "entry_source", "ocr_text", "ocr_confidence",
            "verified_by", "verified_at",
        ))
        return Response({"success": True, "purchase_id": purchase.id, "message": "Invoice verified and purchase created."}, status=201)
