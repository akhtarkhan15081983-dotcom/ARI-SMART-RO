import re

from django.apps import apps
from django.db import transaction

from .id_allocator import acquire_allocator_lock
from .models import HumanReadableIdSequence


def _legacy_max(model_label, field_name, prefix, year):
    model = apps.get_model(model_label)
    pattern = re.compile(rf"^{re.escape(prefix)}-{year}-(\d+)$")
    maximum = 0
    values = model.objects.filter(
        **{f"{field_name}__startswith": f"{prefix}-{year}-"}
    ).values_list(field_name, flat=True)
    for value in values.iterator(chunk_size=1000):
        match = pattern.match(str(value or ""))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


def allocate_operational_number(*, namespace, model_label, field_name, prefix, year):
    """Reserve one collision-safe visible number for a namespace/year."""
    with transaction.atomic():
        acquire_allocator_lock(namespace, year)
        sequence, _ = HumanReadableIdSequence.objects.get_or_create(
            namespace=namespace,
            year=year,
            defaults={"next_value": 1},
        )
        sequence = HumanReadableIdSequence.objects.select_for_update().get(pk=sequence.pk)
        high_water = _legacy_max(model_label, field_name, prefix, year)
        value = max(int(sequence.next_value), high_water + 1)
        sequence.next_value = value + 1
        sequence.save(update_fields=["next_value", "updated_at"])
        return value
