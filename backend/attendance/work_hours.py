from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from employees.models import HRPolicy
from .models import Attendance, OvertimeRequest


TWO_PLACES = Decimal("0.01")


def _hours_between(start, end):
    if not start or not end or end <= start:
        return Decimal("0.00")
    return (Decimal(str((end - start).total_seconds())) / Decimal("3600")).quantize(
        TWO_PLACES,
        rounding=ROUND_HALF_UP,
    )


def regular_shift_end(attendance):
    if not attendance.check_in:
        return None
    if attendance.regular_shift_end_at:
        return attendance.regular_shift_end_at
    hours = float(HRPolicy.current().daily_work_hours)
    return attendance.check_in + timedelta(hours=hours)


def recalculate_attendance(attendance, *, now=None, save=True):
    now = now or timezone.now()
    changed = []

    shift_end = regular_shift_end(attendance)
    if attendance.check_in and not attendance.regular_shift_end_at:
        attendance.regular_shift_end_at = shift_end
        changed.append("regular_shift_end_at")

    if attendance.check_in:
        regular_end = attendance.check_out or min(now, shift_end)
        if regular_end > shift_end:
            regular_end = shift_end
        regular_hours = _hours_between(attendance.check_in, regular_end)
        if attendance.regular_working_hours != regular_hours:
            attendance.regular_working_hours = regular_hours
            changed.append("regular_working_hours")

    if (
        attendance.check_in
        and not attendance.check_out
        and shift_end
        and now >= shift_end
    ):
        attendance.check_out = shift_end
        attendance.auto_checked_out = True
        attendance.checkout_reason = "AUTO_8_HOURS"
        attendance.regular_working_hours = _hours_between(attendance.check_in, shift_end)
        changed.extend([
            "check_out",
            "auto_checked_out",
            "checkout_reason",
            "regular_working_hours",
        ])

    overtime = None
    try:
        overtime = attendance.overtime_request
    except OvertimeRequest.DoesNotExist:
        overtime = None

    overtime_hours = Decimal("0.00")
    if overtime and overtime.started_at:
        overtime_end = overtime.ended_at or min(now, overtime.planned_end_at or now)
        if overtime.planned_end_at and now >= overtime.planned_end_at and not overtime.ended_at:
            overtime.ended_at = overtime.planned_end_at
            overtime.end_reason = "AUTO_APPROVED_LIMIT"
            overtime.status = "COMPLETED"
            overtime.save(update_fields=["ended_at", "end_reason", "status", "updated_at"])
            overtime_end = overtime.ended_at
        overtime_hours = _hours_between(overtime.started_at, overtime_end)

    if attendance.overtime_working_hours != overtime_hours:
        attendance.overtime_working_hours = overtime_hours
        changed.append("overtime_working_hours")

    total = (Decimal(attendance.regular_working_hours or 0) + overtime_hours).quantize(
        TWO_PLACES,
        rounding=ROUND_HALF_UP,
    )
    if attendance.working_hours != total:
        attendance.working_hours = total
        changed.append("working_hours")

    if save and changed:
        attendance.save(update_fields=list(dict.fromkeys(changed)))
    return attendance


def reconcile_open_attendance(*, now=None, employee=None):
    now = now or timezone.now()
    rows = Attendance.objects.filter(check_in__isnull=False)
    if employee is not None:
        rows = rows.filter(employee=employee)
    rows = rows.filter(date__lte=timezone.localdate())
    for attendance in rows.select_related("employee"):
        recalculate_attendance(attendance, now=now, save=True)


def overtime_payload(attendance):
    try:
        row = attendance.overtime_request
    except OvertimeRequest.DoesNotExist:
        return None
    return {
        "id": row.id,
        "status": row.status,
        "requested_hours": str(row.requested_hours),
        "approved_hours": str(row.approved_hours),
        "reason": row.reason,
        "requested_at": row.requested_at,
        "reviewed_at": row.reviewed_at,
        "review_note": row.review_note,
        "started_at": row.started_at,
        "planned_end_at": row.planned_end_at,
        "ended_at": row.ended_at,
        "end_reason": row.end_reason,
        "approved_by": (
            row.reviewed_by.get_full_name() or row.reviewed_by.phone
            if row.reviewed_by
            else None
        ),
    }
