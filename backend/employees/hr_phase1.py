from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.access import HasRequiredFeature, has_feature_access, request_company

from . import hr_lifecycle as legacy_lifecycle
from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .models import EmployeeDocument, EmployeeProfile


DOCUMENT_TYPES = (
    "PHOTO",
    "AADHAAR",
    "PAN",
    "ADDRESS_PROOF",
    "BANK_PROOF",
    "QUALIFICATION",
    "PREVIOUS_EMPLOYMENT",
    "OTHER",
)
MANDATORY_DOCUMENT_TYPES = DOCUMENT_TYPES[:-1]
DOCUMENT_EVENT_TYPES = {
    "DOCUMENT_UPLOADED",
    "DOCUMENT_VERIFIED",
    "DOCUMENT_REJECTED",
    "DOCUMENT_EXPIRED",
}
READY_STATUS_BY_TYPE = {
    "PROBATION": "PROBATION",
    "PERMANENT": "CONFIRMED",
    "CONTRACT": "CONFIRMED",
    "TRAINEE": "PROBATION",
}

# Reuse the existing readiness engine and existing lifecycle-event audit trail.
legacy_lifecycle.REQUIRED_DOCUMENT_TYPES = MANDATORY_DOCUMENT_TYPES
_legacy_readiness = legacy_lifecycle._readiness


def _safe_readiness(employee, lifecycle):
    """Prevent the legacy readiness engine from ever persisting type names as invalid statuses."""
    actual_type = lifecycle.employment_type
    guarded = lifecycle.employment_status == "ONBOARDING" and actual_type != "PROBATION"
    if guarded:
        lifecycle.employment_type = "PROBATION"
    result = _legacy_readiness(employee, lifecycle)
    if guarded:
        lifecycle.employment_type = actual_type
        if result["stage"] == "READY":
            desired_status = READY_STATUS_BY_TYPE[actual_type]
            if lifecycle.employment_status != desired_status:
                lifecycle.employment_status = desired_status
                lifecycle.save(update_fields=["employment_status", "updated_at"])
    valid_statuses = {value for value, _ in EmployeeHrLifecycle.EMPLOYMENT_STATUSES}
    if lifecycle.employment_status not in valid_statuses:
        lifecycle.employment_status = READY_STATUS_BY_TYPE.get(actual_type, "ONBOARDING")
        lifecycle.save(update_fields=["employment_status", "updated_at"])
    return result


legacy_lifecycle._readiness = _safe_readiness


def _role(request):
    return str(getattr(request.user, "role", "") or "").strip().upper()


def _employee_for_request(request, employee_id):
    company = request_company(request)
    if company is None:
        return None
    return EmployeeProfile.objects.filter(pk=employee_id, company=company).select_related(
        "user", "company"
    ).first()


def _can_manage_documents(request):
    return has_feature_access(request, "hrms_documents_manage")


def _can_manage_lifecycle(request):
    role = _role(request)
    return role == "ADMIN" or (
        role == "OFFICE" and has_feature_access(request, "employee_management")
    )


def _document_events(employee):
    events = employee.hr_lifecycle_events.filter(
        event_type__in=DOCUMENT_EVENT_TYPES
    ).select_related("created_by").order_by("-created_at")
    latest = {}
    history = {}
    for event in events:
        document_id = (event.metadata or {}).get("document_id")
        if not isinstance(document_id, int):
            continue
        history.setdefault(document_id, []).append(event)
        latest.setdefault(document_id, event)
    return latest, history


def _effective_document_status(row, latest_event=None):
    today = timezone.localdate()
    if row.expiry_date is not None and row.expiry_date < today:
        return "EXPIRED"
    if latest_event is not None:
        status = str((latest_event.metadata or {}).get("document_status") or "").upper()
        if status in {"UPLOADED", "VERIFIED", "REJECTED", "EXPIRED"}:
            return status
    if row.verified:
        return "VERIFIED"
    if row.file:
        return "UPLOADED"
    return "MISSING"


def _actor(event):
    if event is None:
        return ""
    return event.created_by.get_full_name() or event.created_by.phone


def _serialize_document(row, latest_event=None, history=None):
    status = _effective_document_status(row, latest_event)
    audit = [
        {
            "event": event.event_type,
            "status": (event.metadata or {}).get("document_status", ""),
            "reason": event.note,
            "reviewer": _actor(event),
            "created_at": event.created_at,
        }
        for event in (history or [])
    ]
    reviewer_event = latest_event if status in {"VERIFIED", "REJECTED", "EXPIRED"} else None
    return {
        "id": row.id,
        "type": row.document_type,
        "document_type": row.document_type,
        "number": row.document_number,
        "document_number": row.document_number,
        "status": status,
        "mandatory": row.document_type in MANDATORY_DOCUMENT_TYPES,
        "verified": status == "VERIFIED",
        "has_file": bool(row.file),
        "file_name": row.file.name.rsplit("/", 1)[-1] if row.file else "",
        "expiry_date": row.expiry_date,
        "uploaded_at": row.uploaded_at,
        "reviewer": _actor(reviewer_event),
        "reason": reviewer_event.note if reviewer_event is not None else "",
        "audit": audit,
    }


def _document_contract(employee):
    latest, history = _document_events(employee)
    rows = list(employee.hr_documents.all().order_by("document_type", "-uploaded_at", "-id"))
    result = [_serialize_document(row, latest.get(row.id), history.get(row.id, [])) for row in rows]
    present_types = {item["document_type"] for item in result}
    for document_type in MANDATORY_DOCUMENT_TYPES:
        if document_type not in present_types:
            result.append(
                {
                    "id": None,
                    "type": document_type,
                    "document_type": document_type,
                    "number": "",
                    "document_number": "",
                    "status": "MISSING",
                    "mandatory": True,
                    "verified": False,
                    "has_file": False,
                    "file_name": "",
                    "expiry_date": None,
                    "uploaded_at": None,
                    "reviewer": "",
                    "reason": "",
                    "audit": [],
                }
            )
    rank = {"REJECTED": 0, "EXPIRED": 1, "MISSING": 2, "UPLOADED": 3, "VERIFIED": 4}
    result.sort(key=lambda item: (rank.get(item["status"], 9), item["document_type"]))
    return result


def _event(request, employee, row, event_type, document_status, reason):
    return EmployeeHrLifecycleEvent.objects.create(
        employee=employee,
        event_type=event_type,
        from_status="",
        to_status=document_status,
        note=reason,
        metadata={
            "document_id": row.id,
            "document_type": row.document_type,
            "document_status": document_status,
        },
        created_by=request.user,
    )


def _parse_expiry(value):
    if not value:
        return None, None
    try:
        return timezone.datetime.strptime(str(value), "%Y-%m-%d").date(), None
    except (TypeError, ValueError):
        return None, "Valid expiry date is required in YYYY-MM-DD format."


def _save_upload(request, employee):
    document_type = str(request.data.get("document_type") or "").strip().upper()
    if document_type not in DOCUMENT_TYPES:
        return None, Response(
            {"detail": f"Document type must be one of: {', '.join(DOCUMENT_TYPES)}."}, status=400
        )
    upload = request.FILES.get("file")
    if upload is None:
        return None, Response({"detail": "Actual document file upload is required."}, status=400)
    expiry_date, error = _parse_expiry(request.data.get("expiry_date"))
    if error:
        return None, Response({"detail": error}, status=400)
    if document_type == "OTHER":
        row = EmployeeDocument(employee=employee, document_type=document_type)
    else:
        row = (
            EmployeeDocument.objects.filter(employee=employee, document_type=document_type)
            .order_by("-uploaded_at", "-id")
            .first()
            or EmployeeDocument(employee=employee, document_type=document_type)
        )
    row.document_number = str(request.data.get("document_number") or "").strip()[:100]
    row.file = upload
    row.expiry_date = expiry_date
    row.verified = False
    row.save()
    reason = str(request.data.get("reason") or "Document uploaded for HR verification.").strip()
    _event(request, employee, row, "DOCUMENT_UPLOADED", "UPLOADED", reason)
    return row, None


class EmployeeDocumentComplianceAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)
        can_manage = _can_manage_documents(request)
        employees = EmployeeProfile.objects.filter(company=company).select_related("user")
        if not can_manage:
            employees = employees.filter(user=request.user)
        employee_id = request.query_params.get("employee_id")
        if employee_id and can_manage:
            employees = employees.filter(pk=employee_id)
        documents = []
        for employee in employees[:500]:
            for item in _document_contract(employee):
                if item["id"] is None and not employee_id:
                    continue
                documents.append({**item, "employee_id": employee.id, "employee_name": employee.user.get_full_name() or employee.user.phone})
        return Response({"documents": documents, "document_types": DOCUMENT_TYPES})

    @transaction.atomic
    def post(self, request):
        if not _can_manage_documents(request):
            return Response({"detail": "Document management permission is required."}, status=403)
        employee = _employee_for_request(request, request.data.get("employee_id"))
        if employee is None:
            return Response({"detail": "Employee not found in active company."}, status=404)
        row, error = _save_upload(request, employee)
        if error is not None:
            return error
        latest, history = _document_events(employee)
        return Response(_serialize_document(row, latest.get(row.id), history.get(row.id, [])), status=201)


class EmployeeDocumentWorkflowAPIView(APIView):
    permission_classes = [IsAuthenticated, HasRequiredFeature]
    required_feature = "hrms"

    def get(self, request, employee_id):
        employee = _employee_for_request(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        if not _can_manage_documents(request) and employee.user_id != request.user.id:
            return Response({"detail": "Document access permission is required."}, status=403)
        return Response({
            "employee_id": employee.id,
            "documents": _document_contract(employee),
            "document_types": DOCUMENT_TYPES,
            "mandatory_document_types": MANDATORY_DOCUMENT_TYPES,
        })

    @transaction.atomic
    def post(self, request, employee_id):
        if not _can_manage_documents(request):
            return Response({"detail": "Document management permission is required."}, status=403)
        employee = _employee_for_request(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        row, error = _save_upload(request, employee)
        if error is not None:
            return error
        latest, history = _document_events(employee)
        return Response(_serialize_document(row, latest.get(row.id), history.get(row.id, [])), status=201)

    @transaction.atomic
    def patch(self, request, employee_id):
        if not _can_manage_documents(request):
            return Response({"detail": "Document management permission is required."}, status=403)
        employee = _employee_for_request(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        row = EmployeeDocument.objects.filter(pk=request.data.get("document_id"), employee=employee).first()
        if row is None:
            return Response({"detail": "Document not found."}, status=404)
        action = str(request.data.get("action") or "").strip().upper()
        reason = str(request.data.get("reason") or request.data.get("note") or "").strip()
        if action not in {"VERIFY", "REJECT", "EXPIRE"}:
            return Response({"detail": "Action must be VERIFY, REJECT or EXPIRE."}, status=400)
        if not reason:
            return Response({"detail": "Reviewer reason is required for document action."}, status=400)
        if action == "VERIFY":
            if not row.file:
                return Response({"detail": "Missing document file cannot be verified."}, status=409)
            if row.expiry_date is not None and row.expiry_date < timezone.localdate():
                return Response({"detail": "Expired document cannot be verified."}, status=409)
            row.verified = True
            row.save(update_fields=["verified"])
            event_type, document_status = "DOCUMENT_VERIFIED", "VERIFIED"
        elif action == "REJECT":
            row.verified = False
            row.save(update_fields=["verified"])
            event_type, document_status = "DOCUMENT_REJECTED", "REJECTED"
        else:
            row.verified = False
            if row.expiry_date is None or row.expiry_date >= timezone.localdate():
                row.expiry_date = timezone.localdate() - timedelta(days=1)
            row.save(update_fields=["verified", "expiry_date"])
            event_type, document_status = "DOCUMENT_EXPIRED", "EXPIRED"
        _event(request, employee, row, event_type, document_status, reason)
        latest, history = _document_events(employee)
        return Response(_serialize_document(row, latest.get(row.id), history.get(row.id, [])))


class CorporateHrDashboardAPIView(legacy_lifecycle.CorporateHrDashboardAPIView):
    def get(self, request):
        response = super().get(request)
        if response.status_code != 200:
            return response
        company = request_company(request)
        if company is None:
            return response
        today = timezone.localdate()
        expired = EmployeeDocument.objects.filter(
            employee__company=company, expiry_date__lt=today
        ).select_related("employee__user").order_by("expiry_date", "employee__employee_id")[:200]
        actions = [
            {
                "category": "DOCUMENT_COMPLIANCE",
                "action": "EXPIRED_DOCUMENT",
                "status": "EXPIRED",
                "document_id": row.id,
                "document_type": row.document_type,
                "expiry_date": row.expiry_date,
                "employee_id": row.employee_id,
                "employee_code": row.employee.employee_id,
                "employee_name": row.employee.user.get_full_name() or row.employee.user.phone,
            }
            for row in expired
        ]
        response.data["action_queue"] = actions
        response.data.setdefault("compliance", {})["expired_document_actions"] = actions
        return response


class EmployeeDigitalHrFileAPIView(legacy_lifecycle.EmployeeDigitalHrFileAPIView):
    def get(self, request, employee_id):
        response = super().get(request, employee_id)
        if response.status_code != 200:
            return response
        employee = _employee_for_request(request, employee_id)
        if employee is None:
            return Response({"detail": "Employee not found."}, status=404)
        response.data["documents"] = _document_contract(employee)
        response.data["document_types"] = DOCUMENT_TYPES
        return response

    def patch(self, request, employee_id):
        if not _can_manage_lifecycle(request):
            return Response({"detail": "Authorized HR/Admin lifecycle permission is required."}, status=403)
        if "employment_type" in request.data:
            valid_types = {value for value, _ in EmployeeHrLifecycle.EMPLOYMENT_TYPES}
            requested = str(request.data.get("employment_type") or "").upper()
            if requested not in valid_types:
                return Response({"detail": "Invalid employment type."}, status=400)
        return super().patch(request, employee_id)


class EmployeeHrDirectoryAPIView(legacy_lifecycle.EmployeeHrDirectoryAPIView):
    pass


class EmployeeHrLifecycleActionAPIView(legacy_lifecycle.EmployeeHrLifecycleActionAPIView):
    def post(self, request, employee_id):
        action = str(request.data.get("action") or "").strip().upper()
        role = _role(request)
        if action == "MANAGER_REVIEW":
            if role not in {"MANAGER", "ADMIN"}:
                return Response({"detail": "Manager/Admin review permission is required."}, status=403)
        elif action in {"HR_REVIEW", "EXTEND_PROBATION", "CONFIRM", "START_NOTICE", "SEPARATE"}:
            if not _can_manage_lifecycle(request):
                return Response({"detail": "Authorized HR/Admin lifecycle permission is required."}, status=403)
        elif action in {"OVERRIDE_READY", "REMOVE_READY_OVERRIDE"}:
            if role != "ADMIN":
                return Response({"detail": "Only admin can manage Ready for Duty override."}, status=403)
        return super().post(request, employee_id)
