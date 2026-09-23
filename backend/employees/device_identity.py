from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import write_audit_event

from .models import EmployeeProfile


class EmployeeDeviceIdentityMigrationAPIView(APIView):
    """Safely converge legacy attendance identity on the login device identity.

    Older clients stored a separate attendance device id from the app/login device id.
    A same-install upgrade can prove continuity by presenting both values: the request
    header must still match the user's active login device, and the supplied legacy
    value must match the employee's current attendance binding. A login-device reset
    that happened after face enrollment is treated as a phone-change boundary and
    still requires explicit admin re-enrollment.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        employee = (
            EmployeeProfile.objects.select_for_update()
            .select_related("user", "company")
            .filter(user=request.user)
            .first()
        )
        if employee is None:
            return Response(
                {"success": False, "message": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = employee.user
        canonical_device_id = str(
            request.headers.get("X-ARI-Device-ID", "") or ""
        ).strip()[:64]
        bound_login_device_id = str(user.active_login_device_id or "").strip()[:64]
        legacy_attendance_device_id = str(
            request.data.get("legacy_attendance_device_id", "") or ""
        ).strip()[:128]

        if not canonical_device_id or canonical_device_id != bound_login_device_id:
            return Response(
                {
                    "success": False,
                    "message": "Current login device could not be verified.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not legacy_attendance_device_id:
            return Response(
                {
                    "success": False,
                    "message": "Legacy attendance device ID is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if employee.face_enrolled_at is None or not employee.attendance_device_id:
            return Response(
                {
                    "success": False,
                    "message": "No existing attendance device binding is available to migrate.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        current_attendance_device_id = str(employee.attendance_device_id or "").strip()
        if current_attendance_device_id == canonical_device_id:
            return Response(
                {
                    "success": True,
                    "migrated": False,
                    "message": "Attendance device identity is already unified.",
                }
            )

        if current_attendance_device_id != legacy_attendance_device_id:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Legacy attendance identity does not match this employee. "
                        "Admin re-enrollment is required."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if (
            user.login_device_reset_at is not None
            and employee.face_enrolled_at is not None
            and user.login_device_reset_at >= employee.face_enrolled_at
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Login device changed after face enrollment. "
                        "Admin re-enrollment is required."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        employee.attendance_device_id = canonical_device_id
        employee.save(update_fields=["attendance_device_id"])

        write_audit_event(
            request=request,
            action="ATTENDANCE_DEVICE_ID_MIGRATED",
            entity_type="EmployeeProfile",
            entity_id=employee.id,
            company=employee.company,
            before_state={"attendance_device_unified": False},
            after_state={"attendance_device_unified": True},
            metadata={"employee_id": employee.employee_id, "migration": "legacy_to_canonical"},
        )

        return Response(
            {
                "success": True,
                "migrated": True,
                "message": "Attendance device identity migrated successfully.",
            }
        )
