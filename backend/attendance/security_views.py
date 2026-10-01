from django.db import transaction

from rest_framework import status
from rest_framework.response import Response

from accounts.audit import write_audit_event
from employees.models import EmployeeProfile

from .views import CheckInAPIView


_TRUE_VALUES = {"1", "true", "yes", "on"}


class SecureCheckInAPIView(CheckInAPIView):
    """Attendance check-in with anti-fraud and same-day concurrency guards.

    The employee row is locked for the full authoritative check-in path. The
    inherited view therefore re-checks same-day attendance and creates the row
    inside the same transaction, serializing simultaneous/retried check-ins
    without requiring a new production schema migration.
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

        with transaction.atomic():
            try:
                EmployeeProfile.objects.select_for_update().get(user=request.user)
            except EmployeeProfile.DoesNotExist:
                return Response(
                    {"success": False, "message": "Employee Profile Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return super().post(request)
