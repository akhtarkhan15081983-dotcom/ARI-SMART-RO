from django.db.models.signals import post_save
from django.dispatch import receiver

from .location_models import EmployeeLocationPoint
from .models import EmployeeProfile


@receiver(post_save, sender=EmployeeProfile)
def record_employee_location_point(sender, instance, **kwargs):
    """Persist each accepted live-location update for shift route history.

    The live-location API writes last_latitude/last_longitude together with
    last_location_updated. The unique constraint makes unrelated profile saves
    harmless and keeps retries idempotent.
    """
    if (
        not instance.is_online
        or instance.last_latitude is None
        or instance.last_longitude is None
        or instance.last_location_updated is None
    ):
        return

    EmployeeLocationPoint.objects.get_or_create(
        employee=instance,
        captured_at=instance.last_location_updated,
        latitude=instance.last_latitude,
        longitude=instance.last_longitude,
    )
