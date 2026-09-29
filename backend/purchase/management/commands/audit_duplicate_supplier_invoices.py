import json
from collections import defaultdict

from django.core.management.base import BaseCommand

from purchase.invoice_identity import normalize_invoice_number
from purchase.models import Purchase


def invoice_identity_groups():
    groups = defaultdict(list)
    queryset = Purchase.objects.select_related("supplier", "company").order_by("id")
    for purchase in queryset.iterator():
        normalized = normalize_invoice_number(purchase.invoice_number)
        key = (purchase.company_id, purchase.supplier_id, normalized)
        groups[key].append(purchase)
    return groups


def duplicate_invoice_groups():
    groups = invoice_identity_groups()
    duplicates = []
    for (company_id, supplier_id, normalized), rows in sorted(groups.items(), key=lambda item: str(item[0])):
        if not normalized or len(rows) < 2:
            continue
        duplicates.append({
            "company_id": company_id,
            "supplier_id": supplier_id,
            "supplier": rows[0].supplier.name,
            "normalized_invoice_number": normalized,
            "purchase_ids": [row.id for row in rows],
            "raw_invoice_numbers": [row.invoice_number for row in rows],
            "count": len(rows),
        })
    return duplicates


def build_duplicate_invoice_report():
    groups = invoice_identity_groups()
    duplicates = []
    for (company_id, supplier_id, normalized), rows in sorted(groups.items(), key=lambda item: str(item[0])):
        if not normalized or len(rows) < 2:
            continue
        duplicates.append({
            "company_id": company_id,
            "supplier_id": supplier_id,
            "supplier": rows[0].supplier.name,
            "normalized_invoice_number": normalized,
            "purchase_ids": [row.id for row in rows],
            "raw_invoice_numbers": [row.invoice_number for row in rows],
            "count": len(rows),
        })

    valid_identity_groups = {
        key: rows for key, rows in groups.items() if key[2]
    }
    return {
        "mode": "DRY_RUN_ONLY",
        "normalization": "trim + uppercase + remove whitespace; punctuation preserved",
        "total_purchase_count": Purchase.objects.count(),
        "unique_identity_count": len(valid_identity_groups),
        "duplicate_groups": duplicates,
        "duplicate_group_count": len(duplicates),
        "duplicate_row_count": sum(group["count"] for group in duplicates),
        "future_constraint_design": (
            "After production-like rehearsal and cleanup, persist a normalized invoice key "
            "and enforce tenant-local uniqueness on (company, supplier, normalized_invoice_key)."
        ),
    }


class Command(BaseCommand):
    help = "Dry-run audit for duplicate tenant + supplier + normalized invoice numbers. Never writes data."

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="json_path")

    def handle(self, *args, **options):
        report = build_duplicate_invoice_report()
        payload = json.dumps(report, indent=2, default=str)
        json_path = options.get("json_path")
        if json_path:
            with open(json_path, "w", encoding="utf-8") as handle:
                handle.write(payload)
        self.stdout.write(payload)
