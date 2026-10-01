import json
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from purchase.invoice_identity import normalize_invoice_number
from purchase.models import Purchase
from tenancy.inventory_tenant_backfill import build_inventory_ownership_plan


SAFE_OWNERSHIP_STATUSES = {"RESOLVED", "ALREADY_OWNED"}


def projected_purchase_company_ids():
    return {
        decision.pk: decision.company_id
        for decision in build_inventory_ownership_plan()
        if decision.model == "Purchase"
        and decision.status in SAFE_OWNERSHIP_STATUSES
        and decision.company_id is not None
    }


def invoice_identity_groups():
    groups = defaultdict(list)
    projected_company_ids = projected_purchase_company_ids()
    queryset = Purchase.objects.select_related("supplier", "company").order_by("id")
    for purchase in queryset.iterator():
        normalized = normalize_invoice_number(purchase.invoice_number)
        company_id = projected_company_ids.get(purchase.id)
        key = (company_id, purchase.supplier_id, normalized)
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
    blank_identity_purchase_ids = []
    unresolved_company_purchase_ids = []

    for (company_id, supplier_id, normalized), rows in sorted(groups.items(), key=lambda item: str(item[0])):
        if not normalized:
            blank_identity_purchase_ids.extend(row.id for row in rows)
        if company_id is None:
            unresolved_company_purchase_ids.extend(row.id for row in rows)
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

    valid_identity_groups = {key: rows for key, rows in groups.items() if key[2]}
    duplicate_group_count = len(duplicates)
    blank_identity_purchase_ids = sorted(set(blank_identity_purchase_ids))
    unresolved_company_purchase_ids = sorted(set(unresolved_company_purchase_ids))
    blocking_issue_count = (
        duplicate_group_count
        + len(blank_identity_purchase_ids)
        + len(unresolved_company_purchase_ids)
    )
    constraint_ready = blocking_issue_count == 0

    return {
        "mode": "DRY_RUN_ONLY",
        "ownership_source": "projected inventory tenant ownership; no database writes",
        "normalization": "trim + uppercase + remove whitespace; punctuation preserved",
        "total_purchase_count": Purchase.objects.count(),
        "unique_identity_count": len(valid_identity_groups),
        "duplicate_groups": duplicates,
        "duplicate_group_count": duplicate_group_count,
        "duplicate_row_count": sum(group["count"] for group in duplicates),
        "blank_identity_purchase_ids": blank_identity_purchase_ids,
        "blank_identity_row_count": len(blank_identity_purchase_ids),
        "unresolved_company_purchase_ids": unresolved_company_purchase_ids,
        "unresolved_company_row_count": len(unresolved_company_purchase_ids),
        "blocking_issue_count": blocking_issue_count,
        "rehearsal_status": "CLEAN" if constraint_ready else "BLOCKED",
        "constraint_ready": constraint_ready,
        "future_constraint_design": (
            "After production-like rehearsal and cleanup, persist a normalized invoice key "
            "and enforce tenant-local uniqueness on (company, supplier, normalized_invoice_key)."
        ),
    }


class Command(BaseCommand):
    help = "Dry-run audit for duplicate tenant + supplier + normalized invoice numbers. Never writes data."

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="json_path")
        parser.add_argument(
            "--fail-on-conflict",
            action="store_true",
            help=(
                "Exit non-zero when duplicate identities, blank normalized invoices, or "
                "unresolved company ownership would block the future DB constraint."
            ),
        )

    def handle(self, *args, **options):
        report = build_duplicate_invoice_report()
        payload = json.dumps(report, indent=2, default=str)
        json_path = options.get("json_path")
        if json_path:
            with open(json_path, "w", encoding="utf-8") as handle:
                handle.write(payload)
        self.stdout.write(payload)

        if options.get("fail_on_conflict") and not report["constraint_ready"]:
            raise CommandError(
                "Duplicate-invoice rehearsal is BLOCKED: "
                f"{report['blocking_issue_count']} blocking issue(s) detected."
            )
