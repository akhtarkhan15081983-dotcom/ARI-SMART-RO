from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from inventory.models import EngineerBagItem, InventoryAuditLog, InventoryItem, PartRequest
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company


@dataclass(frozen=True)
class InventoryOwnershipDecision:
    model: str
    pk: int
    status: str
    company_id: int | None
    evidence: tuple[tuple[str, int], ...]

    def as_dict(self):
        return {
            "model": self.model,
            "pk": self.pk,
            "status": self.status,
            "company_id": self.company_id,
            "evidence": [
                {"source": source, "company_id": company_id}
                for source, company_id in self.evidence
            ],
        }


def _single_company_id():
    ids = list(Company.objects.order_by("pk").values_list("id", flat=True)[:2])
    return ids[0] if len(ids) == 1 else None


def decide(model, pk, current_company_id, evidence, *, fallback_company_id=None):
    normalized = tuple(sorted({(source, int(cid)) for source, cid in evidence if cid is not None}))
    candidates = {cid for _, cid in normalized}
    if current_company_id is not None:
        normalized = tuple(sorted(set(normalized + (("current_company", int(current_company_id)),))))
        candidates.add(int(current_company_id))
        if len(candidates) > 1:
            return InventoryOwnershipDecision(model, pk, "CONFLICT", None, normalized)
        return InventoryOwnershipDecision(model, pk, "ALREADY_OWNED", int(current_company_id), normalized)
    if not candidates and fallback_company_id is not None:
        fallback_company_id = int(fallback_company_id)
        normalized = (("single_company_database", fallback_company_id),)
        candidates = {fallback_company_id}
    if not candidates:
        return InventoryOwnershipDecision(model, pk, "UNRESOLVED", None, normalized)
    if len(candidates) > 1:
        return InventoryOwnershipDecision(model, pk, "CONFLICT", None, normalized)
    return InventoryOwnershipDecision(model, pk, "RESOLVED", next(iter(candidates)), normalized)


def _candidate_ids(decision):
    values = {company_id for _, company_id in decision.evidence}
    if decision.company_id is not None:
        values.add(decision.company_id)
    return values


def _single_membership_company(user):
    if user is None:
        return None
    ids = list(
        user.company_memberships.filter(is_active=True)
        .values_list("company_id", flat=True)
        .distinct()
    )
    return ids[0] if len(ids) == 1 else None


def build_inventory_ownership_plan():
    decisions = []
    supplier_candidates = {}
    purchase_candidates = {}
    item_candidates = {}
    inventory_candidates = {}
    fallback_company_id = _single_company_id()

    for supplier in Supplier.objects.order_by("pk"):
        evidence = []
        purchase_companies = set()
        for purchase in supplier.purchases.select_related("verified_by").all():
            if purchase.company_id:
                purchase_companies.add(purchase.company_id)
            member_company = _single_membership_company(purchase.verified_by)
            if member_company:
                purchase_companies.add(member_company)
        for company_id in sorted(purchase_companies):
            evidence.append(("purchase_evidence", company_id))
        decision = decide(
            "Supplier",
            supplier.pk,
            supplier.company_id,
            evidence,
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        supplier_candidates[supplier.pk] = _candidate_ids(decision)

    for purchase in Purchase.objects.select_related("supplier", "verified_by").order_by("pk"):
        evidence = [
            ("supplier_evidence", company_id)
            for company_id in sorted(supplier_candidates.get(purchase.supplier_id, set()))
        ]
        if purchase.supplier.company_id:
            evidence.append(("supplier_current", purchase.supplier.company_id))
        member_company = _single_membership_company(purchase.verified_by)
        if member_company:
            evidence.append(("single_verifier_membership", member_company))
        bag_companies = (
            EngineerBagItem.objects.filter(inventory_item__purchase_item__purchase=purchase)
            .exclude(engineer__company_id=None)
            .values_list("engineer__company_id", flat=True)
            .distinct()
        )
        for company_id in bag_companies:
            evidence.append(("bag_engineer", company_id))
        decision = decide(
            "Purchase",
            purchase.pk,
            purchase.company_id,
            evidence,
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        purchase_candidates[purchase.pk] = _candidate_ids(decision)

    for row in PurchaseItem.objects.select_related("purchase").order_by("pk"):
        evidence = [
            ("purchase_evidence", company_id)
            for company_id in sorted(purchase_candidates.get(row.purchase_id, set()))
        ]
        if row.purchase.company_id:
            evidence.append(("purchase_current", row.purchase.company_id))
        decision = decide(
            "PurchaseItem",
            row.pk,
            row.company_id,
            evidence,
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        item_candidates[row.pk] = _candidate_ids(decision)

    for row in InventoryItem.objects.select_related(
        "purchase_item", "bag_item__engineer"
    ).order_by("pk"):
        evidence = [
            ("purchase_item_evidence", company_id)
            for company_id in sorted(item_candidates.get(row.purchase_item_id, set()))
        ]
        if row.purchase_item.company_id:
            evidence.append(("purchase_item_current", row.purchase_item.company_id))
        if hasattr(row, "bag_item") and row.bag_item.engineer.company_id:
            evidence.append(("bag_engineer", row.bag_item.engineer.company_id))
        decision = decide(
            "InventoryItem",
            row.pk,
            row.company_id,
            evidence,
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        inventory_candidates[row.pk] = _candidate_ids(decision)

    for row in EngineerBagItem.objects.select_related(
        "engineer", "inventory_item__purchase_item"
    ).order_by("pk"):
        evidence = [("engineer", row.engineer.company_id)]
        for company_id in sorted(inventory_candidates.get(row.inventory_item_id, set())):
            evidence.append(("inventory_evidence", company_id))
        if row.inventory_item.company_id:
            evidence.append(("inventory_current", row.inventory_item.company_id))
        decisions.append(
            decide(
                "EngineerBagItem",
                row.pk,
                row.company_id,
                evidence,
                fallback_company_id=fallback_company_id,
            )
        )

    for row in PartRequest.objects.select_related("engineer").order_by("pk"):
        decisions.append(
            decide(
                "PartRequest",
                row.pk,
                row.company_id,
                [("engineer", row.engineer.company_id)],
                fallback_company_id=fallback_company_id,
            )
        )

    for row in InventoryAuditLog.objects.select_related(
        "inventory_item__purchase_item", "engineer", "job"
    ).order_by("pk"):
        evidence = []
        for company_id in sorted(inventory_candidates.get(row.inventory_item_id, set())):
            evidence.append(("inventory_evidence", company_id))
        if row.inventory_item.company_id:
            evidence.append(("inventory_current", row.inventory_item.company_id))
        if row.engineer_id:
            evidence.append(("engineer", row.engineer.company_id))
        if row.job_id:
            evidence.append(("job", row.job.company_id))
        decisions.append(
            decide(
                "InventoryAuditLog",
                row.pk,
                row.company_id,
                evidence,
                fallback_company_id=fallback_company_id,
            )
        )

    return decisions


def summarize_inventory_plan(decisions):
    by_model = {}
    for decision in decisions:
        by_model.setdefault(decision.model, Counter())[decision.status] += 1
    return {model: dict(sorted(counter.items())) for model, counter in sorted(by_model.items())}
