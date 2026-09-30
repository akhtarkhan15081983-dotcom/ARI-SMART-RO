from django.utils import timezone

from assets.models import ROAsset

from .smart_care import NOT_CONFIGURED, OVERDUE, asset_health


def sync_ro_health_notifications(user, customer, upsert_notification, today=None):
    """Materialize configured ARI Care reminders into the existing notification center.

    The caller supplies the existing idempotent notification upsert helper to avoid
    an accounts <-> service import cycle. Reminder event keys are deterministic, so
    opening the notification center or retrying sync never creates duplicates.
    """
    if customer is None or customer.company_id is None or not user or not user.is_active:
        return 0

    today = today or timezone.localdate()
    created_or_refreshed = 0
    assets = ROAsset.objects.filter(
        current_customer=customer,
        is_active=True,
    ).select_related("ro_model")

    for asset in assets:
        health = asset_health(customer.company, asset, today=today)
        for part in health["parts"]:
            status = part["health_status"]
            due_date = part["next_due_date"]
            if status == NOT_CONFIGURED or due_date is None:
                continue

            selected = None
            event_suffix = None
            if status == OVERDUE:
                event_suffix = f"overdue:{due_date.isoformat()}"
            else:
                eligible = [
                    reminder
                    for reminder in part["reminders"]
                    if reminder["remind_on"] <= today <= due_date
                ]
                if eligible:
                    selected = max(eligible, key=lambda item: item["remind_on"])
                    event_suffix = (
                        f"reminder:{due_date.isoformat()}:"
                        f"{selected['days_before_due']}"
                    )

            if event_suffix is None:
                continue

            days_overdue = int(part["days_overdue"] or 0)
            days_remaining = part["days_remaining"]
            if status == OVERDUE:
                title = f"ARI Care: {part['part_name']} service overdue"
                message = (
                    f"{part['part_name']} on RO {asset.asset_id} is "
                    f"{days_overdue} day{'s' if days_overdue != 1 else ''} overdue. "
                    "Open Service / My RO to arrange care."
                )
                priority = "CRITICAL"
            else:
                remaining = int(days_remaining or 0)
                title = f"ARI Care: {part['part_name']} service reminder"
                message = (
                    f"{part['part_name']} on RO {asset.asset_id} is due in "
                    f"{remaining} day{'s' if remaining != 1 else ''} "
                    f"({due_date:%d %b %Y})."
                )
                priority = "HIGH" if remaining <= 7 else "NORMAL"

            upsert_notification(
                user,
                f"ari-care:{asset.id}:{part['part_id']}:{event_suffix}",
                title,
                message,
                category="SERVICE",
                priority=priority,
                action="SERVICE",
                action_label="VIEW SERVICE",
                metadata={
                    "kind": "ARI_CARE",
                    "sound_hint": "ari_care_chime",
                    "asset_id": asset.asset_id,
                    "part_id": part["part_id"],
                    "part_name": part["part_name"],
                    "health_status": status,
                    "due_date": due_date.isoformat(),
                    "days_remaining": part["days_remaining"],
                    "days_overdue": part["days_overdue"],
                    "reminder_days_before_due": (
                        selected["days_before_due"] if selected else None
                    ),
                },
            )
            created_or_refreshed += 1

    return created_or_refreshed
