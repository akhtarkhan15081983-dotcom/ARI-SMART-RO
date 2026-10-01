from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import Attendance, OvertimeRequest

from .location_models import EmployeeLocationPoint
from .models import EmployeeProfile


MAX_BATCH_POINTS = 500
MAX_BACKFILL_AGE = timedelta(hours=72)
CLOCK_SKEW = timedelta(minutes=5)


def _parse_timestamp(raw_value):
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    value = parse_datetime(raw)
    if value is None:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _parse_coordinate(raw_value, *, minimum, maximum):
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if value < Decimal(str(minimum)) or value > Decimal(str(maximum)):
        return None
    return value.quantize(Decimal("0.0000001"))


def _attendance_accepts_point(employee, captured_at):
    local_date = timezone.localtime(captured_at).date()
    attendance = Attendance.objects.filter(
        employee=employee,
        date=local_date,
        check_in__isnull=False,
    ).first()
    if attendance is None:
        return False

    if captured_at < attendance.check_in - CLOCK_SKEW:
        return False

    if attendance.check_out is None:
        return True

    if captured_at <= attendance.check_out + CLOCK_SKEW:
        return True

    overtime = OvertimeRequest.objects.filter(
        attendance=attendance,
        status__in=["APPROVED", "COMPLETED"],
        started_at__isnull=False,
    ).first()
    if overtime is None:
        return False

    overtime_end = overtime.ended_at or overtime.planned_end_at or timezone.now()
    return (
        captured_at >= overtime.started_at - CLOCK_SKEW
        and captured_at <= overtime_end + CLOCK_SKEW
    )


class EmployeeLocationBatchAPIView(APIView):
    """Persist delayed GPS history without moving the employee's live marker backwards.

    Mobile clients upload queued points here after reconnecting. The endpoint is
    intentionally idempotent: the EmployeeLocationPoint unique constraint plus
    ignore_conflicts makes a repeated acknowledged batch safe.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            employee = request.user.employee_profile
        except EmployeeProfile.DoesNotExist:
            return Response({"detail": "Employee profile not found."}, status=404)

        raw_points = request.data.get("points")
        if not isinstance(raw_points, list) or not raw_points:
            return Response({"detail": "points must be a non-empty list."}, status=400)
        if len(raw_points) > MAX_BATCH_POINTS:
            return Response(
                {"detail": f"A maximum of {MAX_BATCH_POINTS} points may be uploaded at once."},
                status=400,
            )

        now = timezone.now()
        oldest_allowed = now - MAX_BACKFILL_AGE
        accepted = []
        rejected = {
            "invalid_shape": 0,
            "invalid_coordinate": 0,
            "invalid_timestamp": 0,
            "outside_retention": 0,
            "outside_shift": 0,
        }

        for raw in raw_points:
            if not isinstance(raw, dict):
                rejected["invalid_shape"] += 1
                continue

            latitude = _parse_coordinate(
                raw.get("live_latitude", raw.get("latitude")),
                minimum=-90,
                maximum=90,
            )
            longitude = _parse_coordinate(
                raw.get("live_longitude", raw.get("longitude")),
                minimum=-180,
                maximum=180,
            )
            if latitude is None or longitude is None:
                rejected["invalid_coordinate"] += 1
                continue

            captured_at = _parse_timestamp(raw.get("captured_at"))
            if captured_at is None:
                rejected["invalid_timestamp"] += 1
                continue
            if captured_at > now + CLOCK_SKEW or captured_at < oldest_allowed:
                rejected["outside_retention"] += 1
                continue
            if not _attendance_accepts_point(employee, captured_at):
                rejected["outside_shift"] += 1
                continue

            accepted.append(
                EmployeeLocationPoint(
                    employee=employee,
                    latitude=latitude,
                    longitude=longitude,
                    captured_at=captured_at,
                )
            )

        if accepted:
            EmployeeLocationPoint.objects.bulk_create(
                accepted,
                ignore_conflicts=True,
                batch_size=250,
            )

        rejected_count = sum(rejected.values())
        return Response(
            {
                "received_count": len(raw_points),
                "accepted_count": len(accepted),
                "rejected_count": rejected_count,
                "rejected": rejected,
                "idempotent": True,
                "max_batch_points": MAX_BATCH_POINTS,
                "retention_hours": int(MAX_BACKFILL_AGE.total_seconds() // 3600),
            }
        )
