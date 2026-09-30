from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import write_audit_event
from employees.models import EmployeeProfile

from .models import Attendance, AttendanceDeviceOverride
from .security import (
    OFFICE_LATITUDE,
    OFFICE_LONGITUDE,
    OFFICE_RADIUS_METERS,
    distance_from_office_meters,
    is_inside_office_geofence,
)
from .serializers import AttendanceSerializer
from .work_hours import recalculate_attendance, regular_shift_end


_TRUE_VALUES = {"1", "true", "yes", "on"}
_MAX_OFFLINE_AGE = timedelta(hours=24)
_MAX_FUTURE_SKEW = timedelta(minutes=5)
_MAX_SELFIE_BYTES = 10 * 1024 * 1024


def _error(message, *, code, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"success": False, "code": code, "message": message},
        status=http_status,
    )


def _parse_captured_at(raw):
    value = parse_datetime(str(raw or "").strip())
    if value is None or timezone.is_naive(value):
        return None
    return value


def _audit(request, employee, *, action, action_id, captured_at, delay_seconds):
    write_audit_event(
        request=request,
        action="ATTENDANCE_OFFLINE_SYNC_APPLIED",
        entity_type="EmployeeProfile",
        entity_id=employee.id,
        company=getattr(employee, "company", None),
        reason=f"Offline attendance {action.lower()} synced after connectivity returned.",
        metadata={
            "employee_id": employee.employee_id,
            "offline_action": action,
            "action_id": action_id,
            "captured_at": captured_at.isoformat(),
            "delay_seconds": max(0, int(delay_seconds)),
        },
    )


class OfflineAttendanceSyncAPIView(APIView):
    """Apply a delayed attendance action captured while the phone was offline.

    The endpoint deliberately re-runs the important attendance security gates.
    Client timestamps are accepted only in a narrow delayed-sync window and are
    kept under human selfie review. Existing attendance for the same date makes
    retries idempotent, including the common case where the original response
    was lost after the server had already committed the action.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        employee = EmployeeProfile.objects.filter(user=request.user).first()
        if employee is None:
            return _error(
                "Employee profile not found.",
                code="EMPLOYEE_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        action = str(request.data.get("action") or "").strip().upper()
        if action not in {"CHECK_IN", "CHECK_OUT"}:
            return _error(
                "Offline attendance action must be CHECK_IN or CHECK_OUT.",
                code="INVALID_ACTION",
            )

        action_id = str(request.data.get("action_id") or "").strip()
        if len(action_id) < 12 or len(action_id) > 100:
            return _error(
                "A valid offline attendance action ID is required.",
                code="INVALID_ACTION_ID",
            )

        captured_at = _parse_captured_at(request.data.get("captured_at"))
        if captured_at is None:
            return _error(
                "A timezone-aware captured_at timestamp is required.",
                code="INVALID_CAPTURED_AT",
            )

        now = timezone.now()
        if captured_at > now + _MAX_FUTURE_SKEW:
            return _error(
                "The phone clock is too far ahead. Correct date/time and try again.",
                code="FUTURE_CAPTURE_TIME",
            )
        if now - captured_at > _MAX_OFFLINE_AGE:
            return _error(
                "Offline attendance is older than 24 hours and requires admin review.",
                code="OFFLINE_ACTION_TOO_OLD",
                http_status=status.HTTP_409_CONFLICT,
            )

        event_date = timezone.localtime(captured_at).date()
        existing = Attendance.objects.filter(employee=employee, date=event_date).first()

        if action == "CHECK_IN":
            return self._apply_check_in(
                request,
                employee=employee,
                existing=existing,
                event_date=event_date,
                action_id=action_id,
                captured_at=captured_at,
                now=now,
            )
        return self._apply_check_out(
            request,
            employee=employee,
            existing=existing,
            action_id=action_id,
            captured_at=captured_at,
            now=now,
        )

    def _apply_check_in(
        self,
        request,
        *,
        employee,
        existing,
        event_date,
        action_id,
        captured_at,
        now,
    ):
        if existing is not None and existing.check_in is not None:
            return Response(
                {
                    "success": True,
                    "message": "Check-in was already recorded; offline retry is complete.",
                    "already_applied": True,
                    "attendance": AttendanceSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        if employee.face_enrolled_at is None or not employee.attendance_device_id:
            return _error(
                "Complete real face/device enrollment before attendance.",
                code="ENROLLMENT_REQUIRED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        if str(request.data.get("is_mocked") or "").strip().lower() in _TRUE_VALUES:
            write_audit_event(
                request=request,
                action="ATTENDANCE_MOCK_LOCATION_BLOCKED",
                entity_type="EmployeeProfile",
                entity_id=employee.id,
                company=getattr(employee, "company", None),
                reason="Device reported mocked/fake GPS in delayed offline attendance.",
                metadata={
                    "employee_id": employee.employee_id,
                    "reported_is_mocked": True,
                    "offline_sync": True,
                    "action_id": action_id,
                },
            )
            return _error(
                "Mock/fake location was detected. Offline check-in cannot be synced.",
                code="MOCK_LOCATION_DETECTED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        device_id = str(request.data.get("device_id") or "").strip()
        override = AttendanceDeviceOverride.objects.filter(
            employee=employee,
            date=event_date,
            is_active=True,
        ).first()
        device_matches = bool(device_id and device_id == employee.attendance_device_id)
        if not device_id:
            return _error("Valid attendance device ID is required.", code="DEVICE_ID_REQUIRED")
        if not device_matches and override is None:
            return _error(
                "Attendance is allowed only from the enrolled device.",
                code="DEVICE_MISMATCH",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        latitude_raw = request.data.get("latitude")
        longitude_raw = request.data.get("longitude")
        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError):
            return _error("Valid GPS coordinates are required.", code="INVALID_GPS")

        distance_meters = distance_from_office_meters(latitude, longitude)
        if not is_inside_office_geofence(latitude, longitude):
            return Response(
                {
                    "success": False,
                    "code": "OUTSIDE_OFFICE_GEOFENCE",
                    "message": (
                        f"Attendance is allowed only within {int(OFFICE_RADIUS_METERS)}m "
                        "of the office."
                    ),
                    "distance_from_office_meters": round(distance_meters, 1),
                    "office": {
                        "latitude": OFFICE_LATITUDE,
                        "longitude": OFFICE_LONGITUDE,
                        "radius_meters": OFFICE_RADIUS_METERS,
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        selfie = request.FILES.get("selfie")
        if selfie is None:
            return _error("A live selfie is required for offline check-in.", code="SELFIE_REQUIRED")
        if getattr(selfie, "size", 0) > _MAX_SELFIE_BYTES:
            return _error("Selfie file is too large.", code="SELFIE_TOO_LARGE")
        content_type = str(getattr(selfie, "content_type", "") or "").lower()
        if content_type and not content_type.startswith("image/"):
            return _error("Selfie must be an image file.", code="INVALID_SELFIE_TYPE")

        used_override = not device_matches and override is not None
        delay_seconds = (now - captured_at).total_seconds()
        remarks = (
            "OFFLINE_SYNC: delayed check-in captured on device and synced after "
            f"connectivity returned; action_id={action_id}."
        )
        if used_override:
            remarks += " Admin-approved emergency attendance device override used."

        attendance = Attendance.objects.create(
            employee=employee,
            date=event_date,
            check_in=captured_at,
            latitude=latitude,
            longitude=longitude,
            selfie=selfie,
            identity_review_status="PENDING",
            remarks=remarks,
        )
        recalculate_attendance(attendance, now=now)
        if used_override:
            override.is_active = False
            override.save(update_fields=["is_active"])

        _audit(
            request,
            employee,
            action="CHECK_IN",
            action_id=action_id,
            captured_at=captured_at,
            delay_seconds=delay_seconds,
        )
        return Response(
            {
                "success": True,
                "message": "Offline check-in synced successfully.",
                "already_applied": False,
                "distance_from_office_meters": round(distance_meters, 1),
                "attendance": AttendanceSerializer(attendance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _apply_check_out(
        self,
        request,
        *,
        employee,
        existing,
        action_id,
        captured_at,
        now,
    ):
        if existing is None or existing.check_in is None:
            return _error(
                "Offline check-out cannot be synced before a check-in exists for that date.",
                code="CHECK_IN_REQUIRED",
                http_status=status.HTTP_409_CONFLICT,
            )
        if existing.check_out is not None:
            return Response(
                {
                    "success": True,
                    "message": "Check-out was already recorded; offline retry is complete.",
                    "already_applied": True,
                    "attendance": AttendanceSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )
        if captured_at < existing.check_in:
            return _error(
                "Offline check-out time cannot be before check-in time.",
                code="CHECK_OUT_BEFORE_CHECK_IN",
                http_status=status.HTTP_409_CONFLICT,
            )

        shift_end = regular_shift_end(existing)
        if shift_end and captured_at >= shift_end:
            existing.check_out = shift_end
            existing.auto_checked_out = True
            existing.checkout_reason = "AUTO_8_HOURS"
        else:
            existing.check_out = captured_at
            existing.auto_checked_out = False
            existing.checkout_reason = "MANUAL"
        marker = f"OFFLINE_SYNC: delayed check-out action_id={action_id}."
        existing.remarks = "\n".join(
            value for value in [existing.remarks.strip(), marker] if value
        )
        existing.save(
            update_fields=["check_out", "auto_checked_out", "checkout_reason", "remarks"]
        )
        recalculate_attendance(existing, now=now)

        _audit(
            request,
            employee,
            action="CHECK_OUT",
            action_id=action_id,
            captured_at=captured_at,
            delay_seconds=(now - captured_at).total_seconds(),
        )
        return Response(
            {
                "success": True,
                "message": "Offline check-out synced successfully.",
                "already_applied": False,
                "attendance": AttendanceSerializer(existing).data,
            },
            status=status.HTTP_200_OK,
        )
