import re

from django.apps import apps
from django.db import transaction

from .models import HumanReadableIdSequence


def _legacy_max(model_label, field_name, prefix, year):
    model = apps.get_model(model_label)
    pattern = re.compile(rf"^{re.escape(prefix)}-{year}-(\d+)$")
    maximum = 0
    values = model.objects.filter(**{f"{field_name}__startswith": f"{prefix}-{year}-"}).values_list(field_name, flat=True)
    for value in values.iterator():
        match = pattern.match(str(value or ""))
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


def allocate_operational_number(*, namespace, model_label, field_name, prefix, year):
    """Reserve one globally unique visible number for a namespace/year.

    A sequence row is locked while incrementing. On first use, it starts above
    all legacy IDs already stored for that model/year so migration is expand-safe.
    Reserved gaps are acceptable; duplicate visible IDs are not.
    """
    with transaction.atomic():
        sequence, created = HumanReadableIdSequence.objects.get_or_create(
            namespace=namespace,
            year=year,
            defaults={
                "next_value": _legacy_max(model_label, field_name, prefix, year) + 1,
            },
        )
        if not created:
            sequence = HumanReadableIdSequence.objects.select_for_update().get(pk=sequence.pk)
        value = sequence.next_value
        sequence.next_value = value + 1
        sequence.save(update_fields=["next_value", "updated_at"])
        return value
