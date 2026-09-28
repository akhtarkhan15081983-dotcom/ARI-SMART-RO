from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import write_audit_event
from accounts.models import AuthSecurityEvent
from accounts.permissions import IsAdmin
from attendance.models import Attendance, AttendanceDeviceOverride, OvertimeRequest
from attendance.work_hours import reconcile_open_attendance, regular_shift_end
from tenancy.access import request_company

from .models import EmployeeProfile
from .views import UpdateLiveLocationAPIView


class CombinedFaceEnrollmentControlAPIView(APIView):
    """Admin face/device control with a single safe new-phone reset path."""

    permission_classes = [IsAdmin]

    @transaction.atomic
    def post(self, request, employee_id):
        company = request_company(request)
        employees = EmployeeProfile.objects.select_related("user").filter(pk=employee_id)
        if company is not None:
            employees = employees.filter(company=company)
        employee = employees.first()
        if employee is None:
            return Response(
                {"success": False, "message": "Employee not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = str(request.data.get("action") or "").strip().lower()
        if action == "cancel_reenrollment":
            employee.face_enrollment_allowed = False
            employee.save(update_fields=["face_enrollment_allowed"])
            return Response(
                {
                    "success": True,
                    "message": "Face/device re-enrollment permission cancelled.",
                }
            )

        if action != "allow_reenrollment":
            return Response(
                {"success": False, "message": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = employee.user
        previous_login_device_id = str(user.active_login_device_id or "")
        previous_attendance_device_id = str(employee.attendance_device_id or "")

        user.previous_login_device_id = previous_login_device_id
        user.active_login_device_id = ""
        user.login_device_reset_at = timezone.now()
        user.login_device_bound_at = None
        user.save(
            update_fields=[
                "previous_login_device_id",
                "active_login_device_id",
                "login_device_reset_at",
                "login_device_bound_at",
            ]
        )

        employee.attendance_device_id = ""
        employee.face_enrollment_allowed = True
        employee.face_enrollment_verified = False
        employee.save(
            update_fields=[
                "attendance_device_id",
                "face_enrollment_allowed",
                "face_enrollment_verified",
            ]
        )

        AttendanceDeviceOverride.objects.filter(
            employee=employee,
            is_active=True,
        ).update(is_active=False)

        AuthSecurityEvent.objects.create(
            user=user,
            event_type="LOGIN_DEVICE_RESET",
            device_id=str(request.headers.get("X-ARI-Device-ID", "") or "")[:64],
            details={
                "employee_id": employee.id,
                "reset_by_user_id": request.user.id,
                "had_login_device": bool(previous_login_device_id),
                "had_attendance_device": bool(previous_attendance_device_id),
                "combined_new_phone_reset": True,
            },
        )
        write_audit_event(
            request=request,
            action="EMPLOYEE_NEW_PHONE_RESET",
            entity_type="EmployeeProfile",
            entity_id=employee.id,
            company=company,
            before_state={
                "login_device_bound": bool(previous_login_device_id),
                "attendance_device_bound": bool(previous_attendance_device_id),
                "face_enrollment_allowed": False,
            },
            after_state={
                "login_device_bound": False,
                "attendance_device_bound": False,
                "face_enrollment_allowed": True,
            },
            metadata={"employee_id": employee.employee_id},
        )

        return Response(
            {
                "success": True,
                "message": (
                    "New phone allowed. Old login and attendance-device bindings were reset. "
                    "Ask the employee to sign in on the new phone and complete face/device enrollment once."
                ),
                "login_device_bound": False,
                "attendance_device_bound": False,
                "face_enrollment_allowed": True,
            }
        )


class AttendanceAwareLiveLocationAPIView(UpdateLiveLocationAPIView):
    """Live-location endpoint that also enforces the current attendance shift."""

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response({"error": "Employee profile not found."}, status=404)

        reconcile_open_attendance(employee=employee)
        attendance = Attendance.objects.filter(
            employee=employee,
            date=timezone.localdate(),
            check_in__isnull=False,
        ).first()

        active_overtime = False
        if attendance is not None:
            active_overtime = OvertimeRequest.objects.filter(
                attendance=attendance,
                status="APPROVED",
                started_at__isnull=False,
                ended_at__isnull=True,
            ).exists()

        # Preserve the legacy location endpoint for employees who have not
        # checked in yet. This keeps location validation, queued-point handling,
        # device diagnostics and operations-map behavior backward compatible.
        # Only an actual attendance record that has ended may stop tracking.
        if (
            request.data.get("tracking_active") is not False
            and attendance is not None
            and attendance.check_out
            and not active_overtime
        ):
            if employee.is_online:
                employee.is_online = False
                employee.save(update_fields=["is_online"])
            return Response(
                {
                    "message": "Work shift is not active. Live tracking stopped on the server.",
                    "online": False,
                    "shift_active": False,
                    "auto_checked_out": attendance.auto_checked_out,
                    "check_out": attendance.check_out,
                }
            )

        response = super().post(request)
        if isinstance(getattr(response, "data", None), dict):
            if attendance is None:
                # No attendance record means the location API remains usable for
                # pre-check-in diagnostics/operations without telling the phone
                # background service to stop itself.
                response.data["shift_active"] = None
            else:
                response.data["shift_active"] = bool(
                    attendance.check_out is None or active_overtime
                )
                response.data["regular_shift_end_at"] = regular_shift_end(attendance)
                response.data["auto_checked_out"] = attendance.auto_checked_out
        return response
