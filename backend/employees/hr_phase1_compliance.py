from django.utils import timezone

from . import hr_lifecycle


MANDATORY_DOCUMENT_TYPES = (
    "PHOTO",
    "AADHAAR",
    "PAN",
    "ADDRESS_PROOF",
    "BANK_PROOF",
    "QUALIFICATION",
    "PREVIOUS_EMPLOYMENT",
)


def phase1_document_compliance(employee):
    """Corporate Phase-1 document gate: real file + verification + validity."""
    docs = list(employee.hr_documents.all())
    today = timezone.localdate()
    by_type = {}
    for row in docs:
        by_type.setdefault(str(row.document_type or "").upper(), []).append(row)

    missing = []
    for kind in MANDATORY_DOCUMENT_TYPES:
        rows = by_type.get(kind, [])
        has_real_file = any(bool(row.file) for row in rows)
        if not rows or not has_real_file:
            missing.append(kind)

    expired = [
        row for row in docs
        if row.expiry_date is not None and row.expiry_date < today
    ]
    unverified = [
        row for row in docs
        if not row.verified or not row.file
    ]

    valid_required = True
    for kind in MANDATORY_DOCUMENT_TYPES:
        rows = by_type.get(kind, [])
        if not any(
            row.file
            and row.verified
            and (row.expiry_date is None or row.expiry_date >= today)
            for row in rows
        ):
            valid_required = False
            break

    return {
        "missing": missing,
        "missing_count": len(missing),
        "unverified_count": len(unverified),
        "expired_count": len(expired),
        "complete": valid_required,
    }


# Lifecycle views resolve this module-level function at runtime, so replacing it
# here strengthens every existing READY calculation without duplicating models.
hr_lifecycle.REQUIRED_DOCUMENT_TYPES = MANDATORY_DOCUMENT_TYPES
hr_lifecycle._document_compliance = phase1_document_compliance
