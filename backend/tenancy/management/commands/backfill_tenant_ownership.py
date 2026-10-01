import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from complaints.models import Complaint
from customers.models import Customer
from jobs.models import Job
from service.models import Service
from tenancy.tenant_backfill import build_ownership_plan, summarize_plan


MODEL_MAP = {
    "Customer": Customer,
    "Job": Job,
    "Service": Service,
    "Complaint": Complaint,
}


class Command(BaseCommand):
    help = (
        "Audit and optionally backfill explicit tenant ownership. "
        "Dry-run is the default; unresolved/conflicting rows remain untouched."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply only RESOLVED ownership decisions. Default is dry-run.",
        )
        parser.add_argument(
            "--report",
            type=str,
            default="",
            help="Optional path for a JSON audit report.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        decisions = build_ownership_plan()
        payload = {
            "mode": "APPLY" if apply_changes else "DRY_RUN",
            "summary": summarize_plan(decisions),
            "rows": [decision.as_dict() for decision in decisions],
        }

        if apply_changes:
            applied = []
            with transaction.atomic():
                for decision in decisions:
                    if decision.status != "RESOLVED" or decision.company_id is None:
                        continue
                    model = MODEL_MAP[decision.model]
                    row = model.objects.select_for_update().get(pk=decision.pk)
                    if row.company_id is not None:
                        continue
                    row.company_id = decision.company_id
                    row.save(update_fields=["company"])
                    applied.append({
                        "model": decision.model,
                        "pk": decision.pk,
                        "company_id": decision.company_id,
                    })
            payload["applied"] = applied
            payload["applied_count"] = len(applied)
        else:
            payload["applied"] = []
            payload["applied_count"] = 0

        report_path = str(options.get("report") or "").strip()
        if report_path:
            path = Path(report_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            payload["report_path"] = str(path)

        self.stdout.write(json.dumps(payload, sort_keys=True))
