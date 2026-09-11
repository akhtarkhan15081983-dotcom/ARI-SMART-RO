import calendar
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone


RENT_GRACE_DAYS = 3
RENT_DAILY_PENALTY = Decimal("10.00")
RENT_REMINDER_DAYS_BEFORE = 3
RENT_REMINDER_INTERVAL_HOURS = 3


def rent_due_date(customer, month):
    """Return the monthly due date, using the installation day safely."""
    due_day = customer.installation_date.day if customer.installation_date else 1
    last_day = calendar.monthrange(month.year, month.month)[1]
    return date(month.year, month.month, min(due_day, last_day))


def rent_penalty(balance, due_date, as_of=None):
    """₹10/day starts on the fourth calendar day after an unpaid due date."""
    as_of = as_of or timezone.localdate()
    balance = Decimal(balance or 0)
    if balance <= 0:
        return {"penalty_days": 0, "penalty_amount": Decimal("0.00")}
    penalty_start = due_date + timedelta(days=RENT_GRACE_DAYS + 1)
    days = max(0, (as_of - penalty_start).days + 1)
    return {
        "penalty_days": days,
        "penalty_amount": RENT_DAILY_PENALTY * Decimal(days),
    }


def rent_alert_schedule(due_date, now=None):
    """Describe the three-hour reminder window beginning three days before due."""
    now = now or timezone.now()
    tz = timezone.get_current_timezone()
    starts_at = timezone.make_aware(
        datetime.combine(due_date - timedelta(days=RENT_REMINDER_DAYS_BEFORE), time.min),
        tz,
    )
    ends_at = timezone.make_aware(
        datetime.combine(due_date + timedelta(days=RENT_GRACE_DAYS), time.max),
        tz,
    )
    active = starts_at <= now <= ends_at
    if now < starts_at:
        next_alert_at = starts_at
    elif active:
        elapsed_hours = int((now - starts_at).total_seconds() // 3600)
        next_slot = ((elapsed_hours // RENT_REMINDER_INTERVAL_HOURS) + 1) * RENT_REMINDER_INTERVAL_HOURS
        next_alert_at = starts_at + timedelta(hours=next_slot)
    else:
        next_alert_at = None
    return {
        "active": active,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "next_alert_at": next_alert_at,
        "repeat_interval_hours": RENT_REMINDER_INTERVAL_HOURS,
    }
