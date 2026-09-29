from __future__ import annotations

import re
from typing import Callable

from django.db import connection, models, transaction
from django.utils import timezone


class HumanReadableIdSequence(models.Model):
    """Serialized allocator state for operational human-readable identifiers."""

    scope = models.CharField(max_length=40)
    year = models.PositiveSmallIntegerField()
    next_value = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tenancy"
        db_table = "tenancy_human_readable_id_sequence"
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "year"],
                name="unique_human_id_scope_year",
            )
        ]


def _table_available() -> bool:
    try:
        return HumanReadableIdSequence._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


def _existing_high_water(model, field_name: str, prefix: str, year: int) -> int:
    marker = f"{prefix}-{year}-"
    high = 0
    values = model.objects.filter(
        **{f"{field_name}__startswith": marker}
    ).values_list(field_name, flat=True)
    pattern = re.compile(rf"^{re.escape(marker)}(\d+)$")
    for value in values.iterator(chunk_size=1000):
        match = pattern.match(str(value or ""))
        if match:
            high = max(high, int(match.group(1)))
    return high


def allocate_identifier(*, scope: str, prefix: str, model, field_name: str, year: int | None = None) -> str | None:
    """Allocate one collision-safe ID.

    Returns None only while historical migrations are running before the
    allocator table exists; model legacy save logic may then run in that
    single-threaded migration context.
    """

    if not _table_available():
        return None

    year = int(year or timezone.now().year)
    lock_key = f"ari-human-id:{scope}:{year}"

    with transaction.atomic():
        if connection.vendor == "postgresql":
            # Serializes first-use too, when no sequence row exists yet.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [lock_key])

        sequence, _ = HumanReadableIdSequence.objects.select_for_update().get_or_create(
            scope=scope,
            year=year,
            defaults={"next_value": 1},
        )

        # Seed safely above imported/legacy identifiers. This is intentionally
        # repeated under the lock so a manually imported higher identifier can
        # never be collided with later.
        high_water = _existing_high_water(model, field_name, prefix, year)
        number = max(int(sequence.next_value), high_water + 1)

        while model.objects.filter(
            **{field_name: f"{prefix}-{year}-{number:06d}"}
        ).exists():
            number += 1

        sequence.next_value = number + 1
        sequence.save(update_fields=["next_value", "updated_at"])
        return f"{prefix}-{year}-{number:06d}"


def _preallocate_customer(original: Callable):
    def save(instance, *args, **kwargs):
        if not instance.customer_id:
            from customers.models import Customer

            identifier = allocate_identifier(
                scope="CUSTOMER",
                prefix="CUS",
                model=Customer,
                field_name="customer_id",
            )
            if identifier:
                instance.customer_id = identifier
                if not instance.card_number:
                    instance.card_number = "ARI-" + identifier[len("CUS-") :]
        return original(instance, *args, **kwargs)

    return save


def _preallocate_job(original: Callable):
    def save(instance, *args, **kwargs):
        if not instance.job_id:
            from jobs.models import Job

            identifier = allocate_identifier(
                scope="JOB",
                prefix="JOB",
                model=Job,
                field_name="job_id",
            )
            if identifier:
                instance.job_id = identifier
        return original(instance, *args, **kwargs)

    return save


def _preallocate_service(original: Callable):
    def save(instance, *args, **kwargs):
        if not instance.service_id:
            from service.models import Service

            identifier = allocate_identifier(
                scope="SERVICE",
                prefix="SER",
                model=Service,
                field_name="service_id",
            )
            if identifier:
                instance.service_id = identifier
        return original(instance, *args, **kwargs)

    return save


def _preallocate_complaint(original: Callable):
    def save(instance, *args, **kwargs):
        if not instance.complaint_id:
            from complaints.models import Complaint

            identifier = allocate_identifier(
                scope="COMPLAINT",
                prefix="CMP",
                model=Complaint,
                field_name="complaint_id",
            )
            if identifier:
                instance.complaint_id = identifier
        return original(instance, *args, **kwargs)

    return save


def install_human_readable_id_hardening() -> None:
    """Install pre-allocation wrappers without changing model business logic."""

    from complaints.models import Complaint
    from customers.models import Customer
    from jobs.models import Job
    from service.models import Service

    targets = (
        (Customer, _preallocate_customer),
        (Job, _preallocate_job),
        (Service, _preallocate_service),
        (Complaint, _preallocate_complaint),
    )
    for model, wrapper in targets:
        if getattr(model, "_max_pro_safe_id_allocator_installed", False):
            continue
        model.save = wrapper(model.save)
        model._max_pro_safe_id_allocator_installed = True
