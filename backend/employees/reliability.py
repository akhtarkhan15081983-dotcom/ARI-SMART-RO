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
from .views import FaceEnrollmentAPIView, UpdateLiveLocationAPIView


class SecureFaceEnrollmentAPIView(FaceEnrollmentAPIView):
    """Face/device enrollment bound to the same authenticated app installation."""

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        supplied_device_id = str(request.data.get("device_id") or "").strip()
        login_device_id = str(request.user.active_login_device_id or "").strip()
        header_device_id = str(request.headers.get("X-ARI-Device-ID", "") or "").strip()

        # Normal authenticated app traffic must always arrive with an active
        # login-device binding; VerifiedCustomerJWTAuthentication enforces this
        # before the view. The narrow fallback below only supports legacy/unbound
        # records after an explicit admin face-reenrollment grant. It does not
        # permit a device move when a login device is already bound.
        legacy_admin_authorized_recovery = bool(
            not login_device_id
            and employee.face_enrollment_allowed
            and supplied_device_id
            and not header_device_id
        )

        if not login_device_id and not legacy_admin_authorized_recovery:
            return Response(
                {
                    "success": False,
                    "code": "LOGIN_DEVICE_NOT_BOUND",
                    "message": "Sign in on the approved phone before face/device enrollment.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if login_device_id and (
            not supplied_device_id
            or supplied_device_id != login_device_id
            or (header_device_id and header_device_id != login_device_id)
        ):
            write_audit_event(
                request=request,
                action="FACE_ENROLLMENT_DEVICE_MISMATCH_BLOCKED",
                entity_type="EmployeeProfile",
                entity_id=employee.id,
                company=getattr(employee, "company", None),
                reason="Face/device enrollment attempted with a device other than the authenticated login device.",
                metadata={
                    "employee_id": employee.employee_id,
                    "login_device_bound": bool(login_device_id),
                    "supplied_device_matches": supplied_device_id == login_device_id,
                    "header_device_matches": (
                        not header_device_id or header_device_id == login_device_id
                    ),
                },
            )
            return Response(
                {
                    "success": False,
                    "code": "FACE_ENROLLMENT_DEVICE_MISMATCH",
                    "message": (
                        "Face/device enrollment must be completed on the same approved phone. "
                        "Ask Admin to reset the device before moving to a new phone."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        response = super().post(request)
        if response.status_code in {status.HTTP_200_OK, status.HTTP_201_CREATED}:
            if legacy_admin_authorized_recovery:
                request.user.active_login_device_id = supplied_device_id[:64]
                request.user.login_device_bound_at = timezone.now()
                request.user.save(
                    update_fields=["active_login_device_id", "login_device_bound_at"]
                )
            write_audit_event(
                request=request,
                action="FACE_DEVICE_ENROLLMENT_COMPLETED",
                entity_type="EmployeeProfile",
                entity_id=employee.id,
                company=getattr(employee, "company", None),
                metadata={
                    "employee_id": employee.employee_id,
                    "device_matches_login_binding": bool(login_device_id),
                    "legacy_admin_authorized_recovery": legacy_admin_authorized_recovery,
                },
            )
        return response


class CombinedFaceEnrollmentControlAPIView(APIView):
    """Admin face/device control with a single safe new-phone reset path."""

    permission_classes = [IsAdmin]

    @transaction.atomic
    def post(self, request, employee_id):
        company = request_company(request)
        employees = EmployeeProfile.objects.select_related("user").filter(pk=employee_id)
        if company is not None:
            employees = employees.filter(company=company)
        else:
            # Legacy records created before tenancy assignment are intentionally
            # limited to company-null employees; never fall back to all tenants.
            employees = employees.filter(company__isnull=True)
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

        # A stop signal must always be accepted, including before check-in or
        # after checkout. New location points, however, are valid only inside a
        # real attendance shift. Returning 2xx + shift_active=false deliberately
        # tells the mobile foreground service to stop without retry-queuing the
        # rejected point.
        if request.data.get("tracking_active") is not False and attendance is None:
            if employee.is_online:
                employee.is_online = False
                employee.save(update_fields=["is_online"])
            return Response(
                {
                    "message": "Check in before live work-location tracking can start.",
                    "online": False,
                    "shift_active": False,
                    "reason": "NO_CHECK_IN",
                }
            )

        active_overtime = False
        if attendance is not None:
            active_overtime = OvertimeRequest.objects.filter(
                attendance=attendance,
                status="APPROVED",
                started_at__isnull=False,
                ended_at__isnull=True,
            ).exists()

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
                    "reason": "SHIFT_ENDED",
                    "auto_checked_out": attendance.auto_checked_out,
                    "check_out": attendance.check_out,
                }
            )

        response = super().post(request)
        if isinstance(getattr(response, "data", None), dict):
            if attendance is None:
                response.data["shift_active"] = None
            else:
                response.data["shift_active"] = bool(
                    attendance.check_out is None or active_overtime
                )
                response.data["regular_shift_end_at"] = regular_shift_end(attendance)
                response.data["auto_checked_out"] = attendance.auto_checked_out
        return response
