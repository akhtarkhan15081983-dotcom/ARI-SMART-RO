from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response

from .views import EngineerLiveMapAPIView


LIVE_FRESH_WINDOW = timedelta(seconds=90)
LOCATION_MISSING_AFTER = timedelta(minutes=3)


def _as_aware_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


class HardenedEngineerLiveMapAPIView(EngineerLiveMapAPIView):
    """Escalate checked-in employees from stale GPS to a critical map state.

    The existing Flutter map renders unknown/non-live/non-missing status values in
    red. We therefore emit LOCATION_MISSING after a three-minute active-shift gap,
    while retaining a machine-readable reason and alert level. The UI text still
    reads "Checked in • GPS missing" and the card/marker becomes red.
    """

    def get(self, request):
        response = super().get(request)
        if response.status_code != 200 or not isinstance(response.data, list):
            return response

        now = timezone.now()
        hardened = []
        for raw_item in response.data:
            if not isinstance(raw_item, dict):
                hardened.append(raw_item)
                continue

            item = dict(raw_item)
            attendance_active = bool(item.get("attendance_active"))
            updated_at = _as_aware_datetime(item.get("updated_at"))

            if updated_at is None:
                item["location_age_seconds"] = None
                if attendance_active:
                    item["location_status"] = "LOCATION_MISSING"
                    item["online"] = False
                    item["location_alert"] = "CRITICAL"
                    item["location_alert_reason"] = "NO_LOCATION_RECEIVED"
                else:
                    item["location_alert"] = "CLEAR"
                    item["location_alert_reason"] = ""
                hardened.append(item)
                continue

            age = max(timedelta(0), now - updated_at)
            item["location_age_seconds"] = int(age.total_seconds())

            if attendance_active and age > LOCATION_MISSING_AFTER:
                item["location_status"] = "LOCATION_MISSING"
                item["online"] = False
                item["location_alert"] = "CRITICAL"
                item["location_alert_reason"] = "GPS_NOT_REFRESHED_3_MIN"
            elif attendance_active and age > LIVE_FRESH_WINDOW:
                item["location_status"] = "STALE"
                item["online"] = False
                item["location_alert"] = "WARNING"
                item["location_alert_reason"] = "GPS_STALE"
            else:
                item["location_alert"] = "CLEAR"
                item["location_alert_reason"] = ""

            hardened.append(item)

        return Response(hardened, status=response.status_code)
