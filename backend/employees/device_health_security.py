from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import write_audit_event
from accounts.permissions import IsAdmin
from tenancy.access import request_company

from .models import EmployeeDeviceHealth, EmployeeProfile
from .views import AdminDeviceHealthAPIView, EmployeeDeviceHealthAPIView


RISK_PREFIX = "SECURITY_RISK["
ATTENDANCE_PENDING_PREFIX = "ATTENDANCE_PENDING["


def _risk_tags(payload):
    tags = []
    if bool(payload.get("root_risk_detected", False)):
        tags.append("ROOT_RISK")
    if bool(payload.get("emulator_detected", False)):
        tags.append("EMULATOR")
    if bool(payload.get("mock_location_detected", False)):
        tags.append("MOCK_LOCATION")
    return tags


def _strip_risk_prefix(value):
    text = str(value or "")
    if not text.startswith(RISK_PREFIX):
        return text
    closing = text.find("]")
    if closing < 0:
        return text
    remainder = text[closing + 1 :].lstrip()
    if remainder.startswith("|"):
        remainder = remainder[1:].lstrip()
    return remainder


def _stored_risks(value):
    text = str(value or "")
    if not text.startswith(RISK_PREFIX):
        return []
    closing = text.find("]")
    if closing < 0:
        return []
    raw = text[len(RISK_PREFIX) : closing]
    return [part.strip() for part in raw.split(",") if part.strip()]


def _pending_attendance(value):
    text = str(value or "")
    start = text.find(ATTENDANCE_PENDING_PREFIX)
    if start < 0:
        return 0
    end = text.find("]", start)
    if end < 0:
        return 0
    raw = text[start + len(ATTENDANCE_PENDING_PREFIX) : end]
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _strip_attendance_pending(value):
    text = str(value or "")
    start = text.find(ATTENDANCE_PENDING_PREFIX)
    if start < 0:
        return text
    end = text.find("]", start)
    if end < 0:
        return text
    before = text[:start].rstrip()
    after = text[end + 1 :].lstrip()
    if before.endswith("|"):
        before = before[:-1].rstrip()
    if after.startswith("|"):
        after = after[1:].lstrip()
    return " | ".join(part for part in (before, after) if part)


def _with_attendance_pending(value, pending):
    base = _strip_attendance_pending(value).strip()
    marker = f"{ATTENDANCE_PENDING_PREFIX}{max(0, int(pending))}]"
    if not base:
        return marker
    max_base = max(0, 500 - len(marker) - 3)
    return f"{base[:max_base]} | {marker}"


class SecurityAwareEmployeeDeviceHealthAPIView(EmployeeDeviceHealthAPIView):
    """Persist normalized device-integrity diagnostics without blocking field work."""

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        payload.setdefault("pending_job_actions", 0)
        payload.setdefault("pending_location_points", 0)
        payload.setdefault("pending_attendance_actions", 0)

        response = super().post(request)
        if response.status_code < 200 or response.status_code >= 300:
            return response

        employee = getattr(request.user, "employee_profile", None)
        if employee is None:
            return response

        try:
            pending_attendance = max(
                0,
                int(payload.get("pending_attendance_actions") or 0),
            )
        except (TypeError, ValueError):
            pending_attendance = 0

        risks = _risk_tags(payload)
        row = EmployeeDeviceHealth.objects.filter(employee=employee).first()
        if row is None:
            return response

        client_error = _strip_attendance_pending(
            _strip_risk_prefix(payload.get("last_error"))
        )[:380]
        if risks:
            summary = f"{RISK_PREFIX}{','.join(risks)}]"
            row.last_error = f"{summary} | {client_error}"[:500] if client_error else summary
            row.save(update_fields=["last_error", "reported_at"])
            write_audit_event(
                request=request,
                action="DEVICE_SECURITY_RISK_REPORTED",
                entity_type="EmployeeDeviceHealth",
                entity_id=row.id,
                company=getattr(employee, "company", None),
                reason="Device integrity risk signal reported by active app installation.",
                metadata={"employee_id": employee.employee_id, "risks": risks},
            )
        elif row.last_error.startswith(RISK_PREFIX):
            row.last_error = client_error

        row.last_error = _with_attendance_pending(row.last_error, pending_attendance)
        row.save(update_fields=["last_error", "reported_at"])

        response.data["security_risks"] = risks
        response.data["risk_level"] = "HIGH" if risks else "CLEAR"
        response.data["pending_attendance_actions"] = pending_attendance
        return response


class SecurityAwareAdminDeviceHealthAPIView(AdminDeviceHealthAPIView):
    def get(self, request):
        response = super().get(request)
        if response.status_code != 200 or not isinstance(response.data, list):
            return response

        for item in response.data:
            if not isinstance(item, dict):
                continue
            health = item.get("health")
            if not isinstance(health, dict):
                item["security_risks"] = []
                item["risk_level"] = "UNKNOWN"
                continue
            stored_error = health.get("last_error")
            risks = _stored_risks(stored_error)
            health["pending_attendance_actions"] = _pending_attendance(stored_error)
            health["last_error"] = _strip_attendance_pending(
                _strip_risk_prefix(stored_error)
            )
            item["security_risks"] = risks
            item["risk_level"] = "HIGH" if risks else "CLEAR"
        return response


class TenantScopedAdminFaceEnrollmentListAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        company = request_company(request)
        employees = EmployeeProfile.objects.filter(
            is_active=True,
            user__is_active=True,
        )
        if company is not None:
            employees = employees.filter(company=company)
        else:
            # Only legacy records that have not yet been assigned to any tenant
            # are visible to an admin without a company membership. This avoids
            # the historical all-company fallback while keeping migration-era
            # unassigned employee records recoverable.
            employees = employees.filter(company__isnull=True)
        employees = employees.select_related("user").order_by(
            "designation", "user__first_name", "user__last_name", "employee_id"
        )
        return Response([
            {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "designation": employee.designation,
                "face_enrolled": bool(employee.face_enrolled_at and employee.photo),
                "face_enrollment_verified": employee.face_enrollment_verified,
                "face_enrollment_allowed": employee.face_enrollment_allowed,
                "attendance_device_bound": bool(employee.attendance_device_id),
            }
            for employee in employees
        ])
