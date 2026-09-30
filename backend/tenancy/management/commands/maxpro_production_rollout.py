import json
import os
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from complaints.models import Complaint
from customers.models import Customer
from inventory.models import EngineerBagItem, InventoryAuditLog, InventoryItem, PartRequest
from jobs.models import Job
from purchase.models import Purchase, PurchaseItem, Supplier
from service.models import Service
from tenancy.inventory_tenant_backfill import build_inventory_ownership_plan, summarize_inventory_plan
from tenancy.management.commands.rehearse_tenant_migration import relation_inconsistencies
from tenancy.tenant_backfill import build_ownership_plan, summarize_plan


EXPECTED_PRODUCTION_DATABASE = "ari_smart_ro"

MODEL_MAP = {
    "Customer": Customer,
    "Job": Job,
    "Service": Service,
    "Complaint": Complaint,
    "Supplier": Supplier,
    "Purchase": Purchase,
    "PurchaseItem": PurchaseItem,
    "InventoryItem": InventoryItem,
    "EngineerBagItem": EngineerBagItem,
    "PartRequest": PartRequest,
    "InventoryAuditLog": InventoryAuditLog,
}


def _status_count(decisions, status):
    return sum(1 for decision in decisions if decision.status == status)


def _summary(operational, warehouse):
    return {
        "operational": summarize_plan(operational),
        "warehouse": summarize_inventory_plan(warehouse),
        "totals": {
            status: _status_count(operational, status) + _status_count(warehouse, status)
            for status in ("ALREADY_OWNED", "RESOLVED", "UNRESOLVED", "CONFLICT")
        },
    }


def _apply_resolved(decisions):
    grouped = defaultdict(list)
    for decision in decisions:
        if decision.status == "RESOLVED" and decision.company_id is not None:
            grouped[(decision.model, int(decision.company_id))].append(decision.pk)

    updated = 0
    for (model_name, company_id), pks in grouped.items():
        model = MODEL_MAP[model_name]
        updated += model.objects.filter(pk__in=pks, company_id__isnull=True).update(company_id=company_id)
    return updated


class Command(BaseCommand):
    help = (
        "Guarded one-time Max-Pro production ownership rollout. It refuses to run unless "
        "the expected production DB is explicitly confirmed and the dry-run has zero "
        "UNRESOLVED/CONFLICT rows."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirm-production-db", action="store_true")
        parser.add_argument("--expected-database-name", required=True)

    def handle(self, *args, **options):
        actual_db = str(connection.settings_dict.get("NAME") or "")
        expected_db = str(options["expected_database_name"] or "")
        confirmed = bool(options["confirm_production_db"])
        env_approved = os.environ.get("ARI_MAXPRO_PRODUCTION_ROLLOUT", "0") == "1"

        if not confirmed or not env_approved:
            raise CommandError("Production rollout requires both explicit CLI and environment approval.")
        if expected_db != EXPECTED_PRODUCTION_DATABASE:
            raise CommandError("Expected database name does not match the hard-coded production database guard.")
        if actual_db != expected_db:
            raise CommandError("Connected database does not match the explicitly expected production database.")

        operational = build_ownership_plan()
        warehouse = build_inventory_ownership_plan()
        before = _summary(operational, warehouse)
        issues_before = relation_inconsistencies()

        if before["totals"]["UNRESOLVED"] or before["totals"]["CONFLICT"] or issues_before:
            self.stdout.write(json.dumps({
                "phase": "DRY_RUN_BLOCKED",
                "database_match": True,
                "summary": before,
                "relation_inconsistency_count": len(issues_before),
                "writes_performed": False,
            }, sort_keys=True))
            raise CommandError("Max-Pro production ownership dry-run is not clean; no writes performed.")

        with transaction.atomic():
            updated_operational = _apply_resolved(operational)
            updated_warehouse = _apply_resolved(warehouse)

            post_operational = build_ownership_plan()
            post_warehouse = build_inventory_ownership_plan()
            after = _summary(post_operational, post_warehouse)
            issues_after = relation_inconsistencies()

            if after["totals"]["UNRESOLVED"] or after["totals"]["CONFLICT"] or after["totals"]["RESOLVED"] or issues_after:
                raise CommandError(
                    "Post-apply verification failed; transaction will be rolled back."
                )

        self.stdout.write(json.dumps({
            "phase": "APPLIED_AND_VERIFIED",
            "database_match": True,
            "dry_run": before,
            "updated_operational": updated_operational,
            "updated_warehouse": updated_warehouse,
            "updated_total": updated_operational + updated_warehouse,
            "post_apply": after,
            "relation_inconsistency_count": len(issues_after),
            "writes_performed": True,
        }, sort_keys=True))
