from django.utils import timezone

from . import hr_lifecycle
from .hr_lifecycle_models import EmployeeHrLifecycleEvent


CORE_REQUIRED_DOCUMENT_TYPES = (
    "PHOTO",
    "AADHAAR",
    "PAN",
    "ADDRESS_PROOF",
    "BANK_PROOF",
)
PHASE1_REQUIRED_DOCUMENT_TYPES = (
    *CORE_REQUIRED_DOCUMENT_TYPES,
    "QUALIFICATION",
    "PREVIOUS_EMPLOYMENT",
)
PHASE1_DOCUMENT_EVENTS = (
    "DOCUMENT_UPLOADED",
    "DOCUMENT_VERIFIED",
    "DOCUMENT_REJECTED",
    "DOCUMENT_EXPIRED",
)


def _uses_phase1_document_workflow(employee):
    return EmployeeHrLifecycleEvent.objects.filter(
        employee=employee,
        event_type__in=PHASE1_DOCUMENT_EVENTS,
    ).exists()


def migration_safe_document_compliance(employee):
    """
    New Phase-1 document workflows enforce all seven corporate document types
    and a real file. Historical employees that have never used the new
    workflow retain the original five-document readiness contract.
    """
    phase1 = _uses_phase1_document_workflow(employee)
    required_types = (
        PHASE1_REQUIRED_DOCUMENT_TYPES if phase1 else CORE_REQUIRED_DOCUMENT_TYPES
    )
    today = timezone.localdate()
    rows = list(employee.hr_documents.all())
    by_type = {}
    for row in rows:
        by_type.setdefault(str(row.document_type or "").upper(), []).append(row)

    missing = []
    unverified_count = 0
    expired_count = 0
    complete = True

    for document_type in required_types:
        candidates = by_type.get(document_type, [])
        if not candidates:
            missing.append(document_type)
            complete = False
            continue

        if phase1 and not any(bool(row.file) for row in candidates):
            missing.append(document_type)
            complete = False

        valid = False
        for row in candidates:
            expired = row.expiry_date is not None and row.expiry_date < today
            if expired:
                expired_count += 1
            if not row.verified:
                unverified_count += 1
            file_ok = bool(row.file) if phase1 else True
            if row.verified and not expired and file_ok:
                valid = True
        if not valid:
            complete = False

    return {
        "missing": missing,
        "missing_count": len(missing),
        "unverified_count": unverified_count,
        "expired_count": expired_count,
        "complete": complete,
        "phase1_document_contract": phase1,
        "required_types": list(required_types),
    }


# Existing lifecycle code resolves these module globals at request time.
hr_lifecycle.REQUIRED_DOCUMENT_TYPES = CORE_REQUIRED_DOCUMENT_TYPES
hr_lifecycle._document_compliance = migration_safe_document_compliance
