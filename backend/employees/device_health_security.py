from rest_framework.response import Response
from rest_framework import status

from accounts.audit import write_audit_event
from accounts.permissions import IsAdmin
from tenancy.access import request_company

from .models import EmployeeDeviceHealth, EmployeeProfile
from .views import EmployeeDeviceHealthAPIView, AdminDeviceHealthAPIView


RISK_PREFIX = "SECURITY_RISK["


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


class SecurityAwareEmployeeDeviceHealthAPIView(EmployeeDeviceHealthAPIView):
    """Persist normalized device-integrity diagnostics without blocking field work."""

    def post(self, request):
        response = super().post(request)
        if response.status_code < 200 or response.status_code >= 300:
            return response

        employee = getattr(request.user, "employee_profile", None)
        if employee is None:
            return response

        payload = request.data if isinstance(request.data, dict) else {}
        risks = _risk_tags(payload)
        row = EmployeeDeviceHealth.objects.filter(employee=employee).first()
        if row is None:
            return response

        client_error = _strip_risk_prefix(payload.get("last_error"))[:380]
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
                metadata={
                    "employee_id": employee.employee_id,
                    "risks": risks,
                },
            )
        elif row.last_error.startswith(RISK_PREFIX):
            row.last_error = client_error
            row.save(update_fields=["last_error", "reported_at"])

        response.data["security_risks"] = risks
        response.data["risk_level"] = "HIGH" if risks else "CLEAR"
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
            risks = _stored_risks(health.get("last_error"))
            health["last_error"] = _strip_risk_prefix(health.get("last_error"))
            item["security_risks"] = risks
            item["risk_level"] = "HIGH" if risks else "CLEAR"
        return response


class TenantScopedAdminFaceEnrollmentListAPIView(Response.__mro__[1]):
    pass


from rest_framework.views import APIView


class TenantScopedAdminFaceEnrollmentListAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        company = request_company(request)
        if company is None:
            return Response(
                {"detail": "Active company workspace not found."},
                status=status.HTTP_403_FORBIDDEN,
            )
        employees = EmployeeProfile.objects.filter(
            company=company,
            is_active=True,
            user__is_active=True,
        ).select_related("user").order_by(
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
