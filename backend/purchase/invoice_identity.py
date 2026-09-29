import re

from .models import Purchase


def normalize_invoice_number(value):
    """Canonical identity used by duplicate audit and runtime write guards.

    Whitespace and case are ignored, while punctuation remains significant.
    """
    return re.sub(r"\s+", "", str(value or "").strip().upper())


def supplier_invoice_exists(*, company_id, supplier_id, invoice_number, exclude_purchase_id=None):
    normalized = normalize_invoice_number(invoice_number)
    if not normalized:
        return False

    queryset = Purchase.objects.filter(company_id=company_id, supplier_id=supplier_id)
    if exclude_purchase_id is not None:
        queryset = queryset.exclude(pk=exclude_purchase_id)

    return any(
        normalize_invoice_number(value) == normalized
        for value in queryset.values_list("invoice_number", flat=True)
    )
