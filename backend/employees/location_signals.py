from django.db.models.signals import post_save
from django.dispatch import receiver

from .location_models import EmployeeLocationPoint
from .location_telemetry import normalize_location_telemetry
from .models import EmployeeProfile


@receiver(post_save, sender=EmployeeProfile)
def record_employee_location_point(sender, instance, **kwargs):
    """Persist each accepted live-location update for shift route history.

    The live-location API writes last_latitude/last_longitude together with
    last_location_updated. V5 attaches normalized optional telemetry to the
    in-memory employee instance before save. Legacy saves remain valid.
    """
    if (
        not instance.is_online
        or instance.last_latitude is None
        or instance.last_longitude is None
        or instance.last_location_updated is None
    ):
        return

    telemetry = normalize_location_telemetry(
        getattr(instance, "_location_telemetry", None) or {}
    )
    defaults = {
        key: value
        for key, value in telemetry.items()
        if value not in (None, "")
    }

    point_id = telemetry.get("client_point_id")
    if point_id:
        EmployeeLocationPoint.objects.get_or_create(
            employee=instance,
            client_point_id=point_id,
            defaults={
                "captured_at": instance.last_location_updated,
                "latitude": instance.last_latitude,
                "longitude": instance.last_longitude,
                **defaults,
            },
        )
        return

    EmployeeLocationPoint.objects.get_or_create(
        employee=instance,
        captured_at=instance.last_location_updated,
        latitude=instance.last_latitude,
        longitude=instance.last_longitude,
        defaults=defaults,
    )
