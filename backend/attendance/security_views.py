from rest_framework import status
from rest_framework.response import Response

from accounts.audit import write_audit_event
from employees.models import EmployeeProfile

from .views import CheckInAPIView


_TRUE_VALUES = {"1", "true", "yes", "on"}


class SecureCheckInAPIView(CheckInAPIView):
    """Attendance check-in with a device-reported mock-location fraud gate.

    The existing server geofence, face/device enrollment and emergency-override
    checks remain authoritative. This adds another anti-fraud signal from the
    mobile OS without weakening any existing check-in behavior.
    """

    def post(self, request):
        is_mocked = str(request.data.get("is_mocked") or "").strip().lower()
        if is_mocked in _TRUE_VALUES:
            employee = EmployeeProfile.objects.filter(user=request.user).first()
            write_audit_event(
                request=request,
                action="ATTENDANCE_MOCK_LOCATION_BLOCKED",
                entity_type="EmployeeProfile",
                entity_id=getattr(employee, "id", ""),
                company=getattr(employee, "company", None),
                reason="Device reported mocked/fake GPS during attendance check-in.",
                metadata={
                    "employee_id": getattr(employee, "employee_id", ""),
                    "reported_is_mocked": True,
                },
            )
            return Response(
                {
                    "success": False,
                    "code": "MOCK_LOCATION_DETECTED",
                    "message": (
                        "Mock/fake location was detected. Disable mock-location apps "
                        "and use the phone's real GPS before checking in."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().post(request)
