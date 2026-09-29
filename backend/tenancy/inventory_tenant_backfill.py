from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from inventory.models import EngineerBagItem, InventoryAuditLog, InventoryItem, PartRequest
from purchase.models import Purchase, PurchaseItem, Supplier


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


def decide(model, pk, current_company_id, evidence):
    normalized = tuple(sorted({(source, int(cid)) for source, cid in evidence if cid is not None}))
    candidates = {cid for _, cid in normalized}
    if current_company_id is not None:
        normalized = tuple(sorted(set(normalized + (("current_company", int(current_company_id)),))))
        candidates.add(int(current_company_id))
        if len(candidates) > 1:
            return InventoryOwnershipDecision(model, pk, "CONFLICT", None, normalized)
        return InventoryOwnershipDecision(model, pk, "ALREADY_OWNED", int(current_company_id), normalized)
    if not candidates:
        return InventoryOwnershipDecision(model, pk, "UNRESOLVED", None, normalized)
    if len(candidates) > 1:
        return InventoryOwnershipDecision(model, pk, "CONFLICT", None, normalized)
    return InventoryOwnershipDecision(model, pk, "RESOLVED", next(iter(candidates)), normalized)


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
    supplier_plan = {}
    purchase_plan = {}
    item_plan = {}
    inventory_plan = {}

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
        decision = decide("Supplier", supplier.pk, supplier.company_id, evidence)
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            supplier_plan[supplier.pk] = decision.company_id

    for purchase in Purchase.objects.select_related("supplier", "verified_by").order_by("pk"):
        evidence = [("supplier", supplier_plan.get(purchase.supplier_id) or purchase.supplier.company_id)]
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
        decision = decide("Purchase", purchase.pk, purchase.company_id, evidence)
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            purchase_plan[purchase.pk] = decision.company_id

    for row in PurchaseItem.objects.select_related("purchase").order_by("pk"):
        authoritative = purchase_plan.get(row.purchase_id) or row.purchase.company_id
        decision = decide("PurchaseItem", row.pk, row.company_id, [("purchase", authoritative)])
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            item_plan[row.pk] = decision.company_id

    for row in InventoryItem.objects.select_related("purchase_item").order_by("pk"):
        authoritative = item_plan.get(row.purchase_item_id) or row.purchase_item.company_id
        evidence = [("purchase_item", authoritative)]
        if hasattr(row, "bag_item") and row.bag_item.engineer.company_id:
            evidence.append(("bag_engineer", row.bag_item.engineer.company_id))
        decision = decide("InventoryItem", row.pk, row.company_id, evidence)
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            inventory_plan[row.pk] = decision.company_id

    for row in EngineerBagItem.objects.select_related("engineer", "inventory_item").order_by("pk"):
        evidence = [
            ("engineer", row.engineer.company_id),
            ("inventory_item", inventory_plan.get(row.inventory_item_id) or row.inventory_item.company_id),
        ]
        decisions.append(decide("EngineerBagItem", row.pk, row.company_id, evidence))

    for row in PartRequest.objects.select_related("engineer").order_by("pk"):
        decisions.append(decide("PartRequest", row.pk, row.company_id, [("engineer", row.engineer.company_id)]))

    for row in InventoryAuditLog.objects.select_related("inventory_item", "engineer", "job").order_by("pk"):
        evidence = [("inventory_item", inventory_plan.get(row.inventory_item_id) or row.inventory_item.company_id)]
        if row.engineer_id:
            evidence.append(("engineer", row.engineer.company_id))
        if row.job_id:
            evidence.append(("job", row.job.company_id))
        decisions.append(decide("InventoryAuditLog", row.pk, row.company_id, evidence))

    return decisions


def summarize_inventory_plan(decisions):
    by_model = {}
    for decision in decisions:
        by_model.setdefault(decision.model, Counter())[decision.status] += 1
    return {model: dict(sorted(counter.items())) for model, counter in sorted(by_model.items())}
