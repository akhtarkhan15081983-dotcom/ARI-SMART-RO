import json
from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from inventory.models import InventoryItem
from purchase.management.commands.audit_duplicate_supplier_invoices import duplicate_invoice_groups
from purchase.models import Purchase


PRODUCTION_DATABASE_NAMES = {"ari_smart_ro"}


@dataclass(frozen=True)
class CleanupCandidate:
    canonical_purchase_id: int
    shell_purchase_ids: tuple[int, ...]

    def as_dict(self):
        return {
            "canonical_purchase_id": self.canonical_purchase_id,
            "shell_purchase_ids": list(self.shell_purchase_ids),
        }


def _current_database_name():
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        return cursor.fetchone()[0]


def _item_signature(purchase):
    return tuple(
        sorted(
            (item.part_id, item.quantity, str(item.purchase_price))
            for item in purchase.items.all()
        )
    )


def _inventory_count(purchase):
    return InventoryItem.objects.filter(purchase_item__purchase=purchase).count()


def _unexpected_reverse_reference_counts(obj, allowed_accessors):
    counts = {}
    for relation in obj._meta.related_objects:
        accessor = relation.get_accessor_name()
        if accessor in allowed_accessors:
            continue
        value = getattr(obj, accessor)
        count = value.count() if hasattr(value, "count") else (1 if value is not None else 0)
        if count:
            counts[relation.related_model._meta.label] = count
    return counts


def build_cleanup_plan():
    candidates = []
    blocked_groups = []

    for group in duplicate_invoice_groups():
        purchases = list(
            Purchase.objects.filter(id__in=group["purchase_ids"])
            .prefetch_related("items")
            .order_by("id")
        )

        if len(purchases) < 2:
            continue

        signatures = {_item_signature(purchase) for purchase in purchases}
        invoice_dates = {purchase.invoice_date for purchase in purchases}
        entry_sources = {purchase.entry_source for purchase in purchases}

        inventory_counts = {
            purchase.id: _inventory_count(purchase)
            for purchase in purchases
        }
        canonical_ids = [
            purchase_id
            for purchase_id, count in inventory_counts.items()
            if count > 0
        ]
        shell_ids = [
            purchase_id
            for purchase_id, count in inventory_counts.items()
            if count == 0
        ]

        reasons = []
        if len(signatures) != 1:
            reasons.append("item_signature_mismatch")
        if len(invoice_dates) != 1:
            reasons.append("invoice_date_mismatch")
        if len(entry_sources) != 1:
            reasons.append("entry_source_mismatch")
        if len(canonical_ids) != 1:
            reasons.append("canonical_purchase_not_unique")
        if not shell_ids:
            reasons.append("no_zero_inventory_shells")

        for purchase in purchases:
            unexpected = _unexpected_reverse_reference_counts(
                purchase,
                allowed_accessors={"items"},
            )
            if unexpected:
                reasons.append(f"purchase_{purchase.id}_unexpected_reverse_refs")

            if purchase.id in shell_ids:
                for item in purchase.items.all():
                    unexpected_item = _unexpected_reverse_reference_counts(
                        item,
                        allowed_accessors={"inventory_items"},
                    )
                    if unexpected_item:
                        reasons.append(f"purchase_item_{item.id}_unexpected_reverse_refs")
                    if item.inventory_items.exists():
                        reasons.append(f"purchase_item_{item.id}_has_inventory")

        if reasons:
            blocked_groups.append({
                "purchase_count": len(purchases),
                "reasons": sorted(set(reasons)),
            })
            continue

        candidates.append(
            CleanupCandidate(
                canonical_purchase_id=canonical_ids[0],
                shell_purchase_ids=tuple(sorted(shell_ids)),
            )
        )

    return candidates, blocked_groups


class Command(BaseCommand):
    help = (
        "Safely identify or remove zero-inventory duplicate purchase shells. "
        "Dry-run by default; apply is explicitly guarded for an isolated rehearsal DB."
    )

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="json_path")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm-rehearsal-db", action="store_true")
        parser.add_argument("--expected-database-name")

    def handle(self, *args, **options):
        database_name = _current_database_name()
        apply_changes = bool(options.get("apply"))
        candidates, blocked_groups = build_cleanup_plan()

        deleted_purchase_count = 0
        deleted_purchase_item_count = 0

        if apply_changes:
            if not options.get("confirm_rehearsal_db"):
                raise CommandError("Refusing write: --confirm-rehearsal-db is required.")
            expected_database_name = options.get("expected_database_name")
            if not expected_database_name:
                raise CommandError("Refusing write: --expected-database-name is required.")
            if database_name != expected_database_name:
                raise CommandError("Refusing write: connected database does not match the expected rehearsal database.")
            if database_name in PRODUCTION_DATABASE_NAMES:
                raise CommandError("Refusing write: production database is protected.")
            if blocked_groups:
                raise CommandError("Refusing write: at least one duplicate group failed cleanup safety checks.")
            if not candidates:
                raise CommandError("Refusing write: no safe duplicate-shell cleanup candidates were found.")

            shell_ids = [
                purchase_id
                for candidate in candidates
                for purchase_id in candidate.shell_purchase_ids
            ]

            with transaction.atomic():
                locked_shells = list(
                    Purchase.objects.select_for_update()
                    .filter(id__in=shell_ids)
                    .prefetch_related("items")
                    .order_by("id")
                )
                if len(locked_shells) != len(shell_ids):
                    raise CommandError("Refusing write: cleanup candidate set changed before apply.")

                for purchase in locked_shells:
                    if _inventory_count(purchase) != 0:
                        raise CommandError("Refusing write: a duplicate shell gained inventory before apply.")
                    if _unexpected_reverse_reference_counts(purchase, allowed_accessors={"items"}):
                        raise CommandError("Refusing write: a duplicate shell gained an unexpected dependency.")
                    for item in purchase.items.all():
                        if item.inventory_items.exists():
                            raise CommandError("Refusing write: a duplicate shell item gained inventory before apply.")
                        if _unexpected_reverse_reference_counts(item, allowed_accessors={"inventory_items"}):
                            raise CommandError("Refusing write: a duplicate shell item gained an unexpected dependency.")

                deleted_purchase_item_count = sum(len(purchase.items.all()) for purchase in locked_shells)
                deleted_purchase_count = len(locked_shells)
                Purchase.objects.filter(id__in=shell_ids).delete()

        report = {
            "mode": "APPLY" if apply_changes else "DRY_RUN_ONLY",
            "writes_performed": apply_changes,
            "database_name_matches_expected": (
                database_name == options.get("expected_database_name")
                if options.get("expected_database_name")
                else None
            ),
            "protected_production_database": database_name in PRODUCTION_DATABASE_NAMES,
            "safe_candidate_group_count": len(candidates),
            "safe_shell_purchase_count": sum(len(candidate.shell_purchase_ids) for candidate in candidates),
            "blocked_group_count": len(blocked_groups),
            "candidates": [candidate.as_dict() for candidate in candidates],
            "blocked_groups": blocked_groups,
            "deleted_purchase_count": deleted_purchase_count,
            "deleted_purchase_item_count": deleted_purchase_item_count,
        }

        payload = json.dumps(report, indent=2)
        if options.get("json_path"):
            with open(options["json_path"], "w", encoding="utf-8") as handle:
                handle.write(payload)
        self.stdout.write(payload)
