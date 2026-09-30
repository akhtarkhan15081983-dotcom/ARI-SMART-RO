from datetime import timedelta

from django.utils import timezone

from .models import Attendance
from .offline_views import OfflineAttendanceSyncAPIView as BaseOfflineAttendanceSyncAPIView


class OfflineAttendanceSyncAPIView(BaseOfflineAttendanceSyncAPIView):
    """Harden delayed checkout when an active shift crosses local midnight.

    Attendance belongs to the local date on which the employee checked in. A
    delayed checkout captured shortly after midnight therefore must still be
    able to close the previous local day's open attendance row. The base view
    remains the source of truth for all security, age, idempotency and
    eight-hour auto-checkout rules; this wrapper only resolves the correct row
    before delegating to it.
    """

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
        if existing is None:
            event_date = timezone.localtime(captured_at).date()
            previous_date = event_date - timedelta(days=1)
            candidate = (
                Attendance.objects.filter(
                    employee=employee,
                    date=previous_date,
                    check_in__isnull=False,
                    check_in__lte=captured_at,
                )
                .order_by("-check_in", "-id")
                .first()
            )
            if candidate is not None:
                elapsed = captured_at - candidate.check_in
                if timedelta(0) <= elapsed <= timedelta(hours=24):
                    existing = candidate

        return super()._apply_check_out(
            request,
            employee=employee,
            existing=existing,
            action_id=action_id,
            captured_at=captured_at,
            now=now,
        )
