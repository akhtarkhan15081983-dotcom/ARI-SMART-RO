import json

from django.core.management.base import BaseCommand

from complaints.models import Complaint
from customers.models import Customer
from inventory.models import EngineerBagItem, InventoryAuditLog, InventoryItem, PartRequest
from jobs.models import Job
from purchase.models import Purchase, PurchaseItem, Supplier
from service.models import Service
from tenancy.inventory_tenant_backfill import build_inventory_ownership_plan, summarize_inventory_plan
from tenancy.tenant_backfill import build_ownership_plan, summarize_plan


OPERATIONAL_MODELS = [Customer, Job, Service, Complaint]
WAREHOUSE_MODELS = [Supplier, Purchase, PurchaseItem, InventoryItem, EngineerBagItem, PartRequest, InventoryAuditLog]


def _counts(models):
    result = {}
    for model in models:
        queryset = model.objects.all()
        result[model.__name__] = {
            "total": queryset.count(),
            "owned": queryset.exclude(company_id=None).count(),
            "unowned": queryset.filter(company_id=None).count(),
        }
    return result


def _projected_counts(models, decisions):
    before = _counts(models)
    resolved_by_model = {}
    for decision in decisions:
        if decision.status == "RESOLVED":
            resolved_by_model[decision.model] = resolved_by_model.get(decision.model, 0) + 1

    projected = {}
    for model in models:
        name = model.__name__
        resolved = resolved_by_model.get(name, 0)
        row = before[name]
        projected[name] = {
            "total": row["total"],
            "owned": row["owned"] + resolved,
            "unowned": max(0, row["unowned"] - resolved),
            "resolved_by_rehearsal": resolved,
        }
    return projected


def _mismatch(row, source, left_id, right_id):
    if left_id is None or right_id is None or left_id == right_id:
        return None
    return {
        "model": row.__class__.__name__,
        "pk": row.pk,
        "relationship": source,
        "record_company_id": left_id,
        "related_company_id": right_id,
    }


def relation_inconsistencies():
    issues = []

    for row in Job.objects.select_related("customer", "engineer"):
        for source, company_id in (
            ("customer", row.customer.company_id),
            ("engineer", row.engineer.company_id),
        ):
            issue = _mismatch(row, source, row.company_id, company_id)
            if issue:
                issues.append(issue)

    for row in Service.objects.select_related("customer", "engineer", "job"):
        related = [("customer", row.customer.company_id), ("engineer", row.engineer.company_id)]
        if row.job_id:
            related.append(("job", row.job.company_id))
        for source, company_id in related:
            issue = _mismatch(row, source, row.company_id, company_id)
            if issue:
                issues.append(issue)

    for row in Complaint.objects.select_related("customer", "engineer", "job", "linked_service"):
        related = [("customer", row.customer.company_id)]
        if row.engineer_id:
            related.append(("engineer", row.engineer.company_id))
        if row.job_id:
            related.append(("job", row.job.company_id))
        if row.linked_service_id:
            related.append(("linked_service", row.linked_service.company_id))
        for source, company_id in related:
            issue = _mismatch(row, source, row.company_id, company_id)
            if issue:
                issues.append(issue)

    for row in Purchase.objects.select_related("supplier"):
        issue = _mismatch(row, "supplier", row.company_id, row.supplier.company_id)
        if issue:
            issues.append(issue)

    for row in PurchaseItem.objects.select_related("purchase"):
        issue = _mismatch(row, "purchase", row.company_id, row.purchase.company_id)
        if issue:
            issues.append(issue)

    for row in InventoryItem.objects.select_related("purchase_item"):
        issue = _mismatch(row, "purchase_item", row.company_id, row.purchase_item.company_id)
        if issue:
            issues.append(issue)

    for row in EngineerBagItem.objects.select_related("engineer", "inventory_item"):
        for source, company_id in (
            ("engineer", row.engineer.company_id),
            ("inventory_item", row.inventory_item.company_id),
        ):
            issue = _mismatch(row, source, row.company_id, company_id)
            if issue:
                issues.append(issue)

    for row in PartRequest.objects.select_related("engineer"):
        issue = _mismatch(row, "engineer", row.company_id, row.engineer.company_id)
        if issue:
            issues.append(issue)

    for row in InventoryAuditLog.objects.select_related("inventory_item", "engineer", "job"):
        related = [("inventory_item", row.inventory_item.company_id)]
        if row.engineer_id:
            related.append(("engineer", row.engineer.company_id))
        if row.job_id:
            related.append(("job", row.job.company_id))
        for source, company_id in related:
            issue = _mismatch(row, source, row.company_id, company_id)
            if issue:
                issues.append(issue)

    return issues


class Command(BaseCommand):
    help = "Read-only migration rehearsal for operational + warehouse tenant ownership."

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="json_path")

    def handle(self, *args, **options):
        operational_plan = build_ownership_plan()
        inventory_plan = build_inventory_ownership_plan()
        issues = relation_inconsistencies()
        report = {
            "mode": "DRY_RUN_ONLY",
            "writes_performed": False,
            "before_counts": {
                "operational": _counts(OPERATIONAL_MODELS),
                "warehouse": _counts(WAREHOUSE_MODELS),
            },
            "projected_after_counts": {
                "operational": _projected_counts(OPERATIONAL_MODELS, operational_plan),
                "warehouse": _projected_counts(WAREHOUSE_MODELS, inventory_plan),
            },
            "projected_backfill": {
                "operational": summarize_plan(operational_plan),
                "warehouse": summarize_inventory_plan(inventory_plan),
            },
            "conflicts": {
                "operational": [row.as_dict() for row in operational_plan if row.status == "CONFLICT"],
                "warehouse": [row.as_dict() for row in inventory_plan if row.status == "CONFLICT"],
            },
            "unresolved": {
                "operational": [row.as_dict() for row in operational_plan if row.status == "UNRESOLVED"],
                "warehouse": [row.as_dict() for row in inventory_plan if row.status == "UNRESOLVED"],
            },
            "relation_inconsistencies": issues,
            "relation_inconsistency_count": len(issues),
        }
        payload = json.dumps(report, indent=2, default=str)
        json_path = options.get("json_path")
        if json_path:
            with open(json_path, "w", encoding="utf-8") as handle:
                handle.write(payload)
        self.stdout.write(payload)
