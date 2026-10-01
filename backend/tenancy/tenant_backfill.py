from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from complaints.models import Complaint
from customers.models import Customer
from jobs.models import Job
from service.models import Service
from tenancy.models import Company


@dataclass(frozen=True)
class OwnershipDecision:
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


def _decision(
    model: str,
    pk: int,
    current_company_id: int | None,
    evidence: Iterable[tuple[str, int | None]],
    *,
    fallback_company_id: int | None = None,
):
    normalized = tuple(
        sorted(
            {(source, int(company_id)) for source, company_id in evidence if company_id is not None},
            key=lambda item: (item[0], item[1]),
        )
    )
    candidate_ids = {company_id for _, company_id in normalized}

    if current_company_id is not None:
        candidate_ids.add(int(current_company_id))
        normalized = tuple(sorted(set(normalized + (("current_company", int(current_company_id)),))))
        if len(candidate_ids) > 1:
            return OwnershipDecision(model, pk, "CONFLICT", None, normalized)
        return OwnershipDecision(model, pk, "ALREADY_OWNED", int(current_company_id), normalized)

    if not candidate_ids and fallback_company_id is not None:
        fallback_company_id = int(fallback_company_id)
        normalized = (("single_company_database", fallback_company_id),)
        candidate_ids = {fallback_company_id}

    if not candidate_ids:
        return OwnershipDecision(model, pk, "UNRESOLVED", None, normalized)
    if len(candidate_ids) > 1:
        return OwnershipDecision(model, pk, "CONFLICT", None, normalized)
    return OwnershipDecision(model, pk, "RESOLVED", next(iter(candidate_ids)), normalized)


def _customer_evidence(customer: Customer):
    evidence: list[tuple[str, int | None]] = []
    if customer.assigned_engineer_id:
        evidence.append(("assigned_engineer", customer.assigned_engineer.company_id))

    for company_id in customer.jobs.exclude(engineer__company_id=None).values_list("engineer__company_id", flat=True).distinct():
        evidence.append(("job_engineer", company_id))
    for company_id in customer.services.exclude(engineer__company_id=None).values_list("engineer__company_id", flat=True).distinct():
        evidence.append(("service_engineer", company_id))
    for company_id in customer.complaints.exclude(engineer__company_id=None).values_list("engineer__company_id", flat=True).distinct():
        evidence.append(("complaint_engineer", company_id))

    if customer.user_id:
        memberships = list(
            customer.user.company_memberships.filter(is_active=True)
            .values_list("company_id", flat=True)
            .distinct()
        )
        if len(memberships) == 1:
            evidence.append(("single_active_user_membership", memberships[0]))
        elif len(memberships) > 1:
            for company_id in memberships:
                evidence.append(("multiple_active_user_membership", company_id))
    return evidence


def build_ownership_plan():
    decisions: list[OwnershipDecision] = []
    planned_customer: dict[int, int] = {}
    planned_job: dict[int, int] = {}
    planned_service: dict[int, int] = {}
    fallback_company_id = _single_company_id()

    for customer in Customer.objects.select_related("assigned_engineer", "user").order_by("pk"):
        decision = _decision(
            "Customer",
            customer.pk,
            customer.company_id,
            _customer_evidence(customer),
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            planned_customer[customer.pk] = decision.company_id

    for job in Job.objects.select_related("customer", "engineer").order_by("pk"):
        evidence = [
            ("customer", planned_customer.get(job.customer_id) or job.customer.company_id),
            ("engineer", job.engineer.company_id),
        ]
        decision = _decision(
            "Job",
            job.pk,
            job.company_id,
            evidence,
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            planned_job[job.pk] = decision.company_id

    for row in Service.objects.select_related("customer", "engineer", "job").order_by("pk"):
        evidence = [
            ("customer", planned_customer.get(row.customer_id) or row.customer.company_id),
            ("engineer", row.engineer.company_id),
        ]
        if row.job_id:
            evidence.append(("job", planned_job.get(row.job_id) or row.job.company_id))
        decision = _decision(
            "Service",
            row.pk,
            row.company_id,
            evidence,
            fallback_company_id=fallback_company_id,
        )
        decisions.append(decision)
        if decision.company_id is not None and decision.status in {"RESOLVED", "ALREADY_OWNED"}:
            planned_service[row.pk] = decision.company_id

    for row in Complaint.objects.select_related("customer", "engineer", "job", "linked_service").order_by("pk"):
        evidence = [("customer", planned_customer.get(row.customer_id) or row.customer.company_id)]
        if row.engineer_id:
            evidence.append(("engineer", row.engineer.company_id))
        if row.job_id:
            evidence.append(("job", planned_job.get(row.job_id) or row.job.company_id))
        if row.linked_service_id:
            evidence.append(("linked_service", planned_service.get(row.linked_service_id) or row.linked_service.company_id))
        decisions.append(
            _decision(
                "Complaint",
                row.pk,
                row.company_id,
                evidence,
                fallback_company_id=fallback_company_id,
            )
        )

    return decisions


def summarize_plan(decisions):
    by_model: dict[str, Counter] = {}
    for decision in decisions:
        by_model.setdefault(decision.model, Counter())[decision.status] += 1
    return {
        model: dict(sorted(counter.items()))
        for model, counter in sorted(by_model.items())
    }
