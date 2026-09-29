from __future__ import annotations

import hashlib

from django.db import connection


def _lock_key(namespace: str, year: int | None = None) -> int:
    """Return a stable signed bigint key for PostgreSQL advisory locks."""
    material = f"{namespace}:{year}" if year is not None else namespace
    raw = hashlib.blake2b(material.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(raw, byteorder="big", signed=False)
    if value >= 2**63:
        value -= 2**64
    return value


def acquire_allocator_lock(namespace: str, year: int | None = None) -> None:
    """Serialize allocation for one logical sequence for the current transaction."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_lock_key(namespace, year)])


def next_visible_number(model, field_name: str, prefix: str, year: int) -> int:
    """Find the next numeric suffix after acquiring the caller's sequence lock."""
    visible_prefix = f"{prefix}-{year}-"
    maximum = 0
    for value in model.objects.filter(**{f"{field_name}__startswith": visible_prefix}).values_list(
        field_name, flat=True
    ):
        try:
            number = int(str(value).rsplit("-", 1)[-1])
        except (TypeError, ValueError):
            continue
        maximum = max(maximum, number)
    return maximum + 1
