import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


PERIOD_CHOICES = {
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "halfyearly",
    "annual",
    "custom",
}


@dataclass(frozen=True)
class ReportPeriod:
    key: str
    start: date
    end: date
    start_datetime: datetime
    end_datetime: datetime

    @property
    def label(self):
        if self.start == self.end:
            return self.start.strftime("%d %b %Y")
        return f"{self.start.strftime('%d %b %Y')} - {self.end.strftime('%d %b %Y')}"

    def as_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
        }


def _parse_optional_date(value, label):
    if not value:
        return None
    parsed = parse_date(str(value))
    if parsed is None:
        raise ValueError(f"{label} must be in YYYY-MM-DD format.")
    return parsed


def resolve_period(params):
    period = str(params.get("period") or "monthly").strip().lower()
    if period not in PERIOD_CHOICES:
        raise ValueError(
            "period must be daily, weekly, monthly, quarterly, halfyearly, annual or custom."
        )

    anchor = _parse_optional_date(params.get("date"), "date") or timezone.localdate()

    if period == "custom":
        start = _parse_optional_date(params.get("start"), "start")
        end = _parse_optional_date(params.get("end"), "end")
        if start is None or end is None:
            raise ValueError("start and end are required for a custom report.")
        if end < start:
            raise ValueError("end cannot be earlier than start.")
        if (end - start).days > 3660:
            raise ValueError("Custom report range cannot exceed 10 years.")
    elif period == "daily":
        start = end = anchor
    elif period == "weekly":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
    elif period == "monthly":
        start = anchor.replace(day=1)
        end = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
    elif period == "quarterly":
        first_month = ((anchor.month - 1) // 3) * 3 + 1
        start = date(anchor.year, first_month, 1)
        end_month = first_month + 2
        end = date(anchor.year, end_month, calendar.monthrange(anchor.year, end_month)[1])
    elif period == "halfyearly":
        first_month = 1 if anchor.month <= 6 else 7
        end_month = 6 if first_month == 1 else 12
        start = date(anchor.year, first_month, 1)
        end = date(anchor.year, end_month, calendar.monthrange(anchor.year, end_month)[1])
    else:
        start = date(anchor.year, 1, 1)
        end = date(anchor.year, 12, 31)

    current_timezone = timezone.get_current_timezone()
    start_datetime = timezone.make_aware(datetime.combine(start, time.min), current_timezone)
    end_datetime = timezone.make_aware(
        datetime.combine(end + timedelta(days=1), time.min),
        current_timezone,
    )
    return ReportPeriod(period, start, end, start_datetime, end_datetime)
