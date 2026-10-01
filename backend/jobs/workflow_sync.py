from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from assets.models import ROAsset
from .models import Job


COMPLAINT_PRIORITY_TO_JOB = {
    "NORMAL": "MEDIUM",
    "URGENT": "HIGH",
    "EMERGENCY": "HIGH",
}


def _active_asset_for_customer(customer):
    return (
        ROAsset.objects
        .filter(current_customer=customer, is_active=True)
        .order_by("-id")
        .first()
    )


def _source_company_id(source):
    candidates = {
        company_id
        for company_id in (
            getattr(source, "company_id", None),
            getattr(getattr(source, "customer", None), "company_id", None),
            getattr(getattr(source, "engineer", None), "company_id", None),
        )
        if company_id is not None
    }
    if len(candidates) > 1:
        raise ValidationError("Operational source has conflicting company ownership.")
    return next(iter(candidates)) if candidates else None


def _update_job_metadata(job, values):
    changed = []
    for field, value in values.items():
        if getattr(job, field) != value:
            setattr(job, field, value)
            changed.append(field)
    if changed:
        job.save(update_fields=changed + ["updated_at"])
    return job


def ensure_complaint_job(complaint):
    if complaint.engineer_id is None:
        return None

    asset = _active_asset_for_customer(complaint.customer)
    company_id = _source_company_id(complaint)
    values = {
        "company_id": company_id,
        "customer": complaint.customer,
        "ro_asset": asset,
        "engineer": complaint.engineer,
        "job_type": "COMPLAINT",
        "priority": COMPLAINT_PRIORITY_TO_JOB.get(complaint.priority, "MEDIUM"),
        "scheduled_date": complaint.scheduled_date or complaint.complaint_date or timezone.now(),
        "remarks": complaint.description or complaint.complaint_id,
    }

    with transaction.atomic():
        if complaint.job_id:
            job = Job.objects.select_for_update().filter(pk=complaint.job_id).first()
            if job is not None:
                if job.company_id not in (None, company_id):
                    raise ValidationError("Complaint job belongs to another company workspace.")
                return _update_job_metadata(job, values)

        job = Job.objects.create(**values, status="ASSIGNED")
        type(complaint).objects.filter(pk=complaint.pk).update(job=job)
        complaint.job_id = job.id
        return job


def ensure_service_job(service):
    if service.engineer_id is None or service.ro_asset_id is None:
        return None

    company_id = _source_company_id(service)
    values = {
        "company_id": company_id,
        "customer": service.customer,
        "ro_asset": service.ro_asset,
        "engineer": service.engineer,
        "job_type": "SERVICE",
        "priority": "MEDIUM",
        "scheduled_date": service.scheduled_date,
        "remarks": service.remarks or service.service_id,
    }

    with transaction.atomic():
        if service.job_id:
            job = Job.objects.select_for_update().filter(pk=service.job_id).first()
            if job is not None:
                if job.company_id not in (None, company_id):
                    raise ValidationError("Service job belongs to another company workspace.")
                return _update_job_metadata(job, values)

        job = Job.objects.create(**values, status="ASSIGNED")
        type(service).objects.filter(pk=service.pk).update(job=job)
        service.job_id = job.id
        return job


def sync_sources_from_job(job):
    now = timezone.now()

    if job.job_type == "COMPLAINT":
        from complaints.models import Complaint

        complaint = Complaint.objects.filter(job=job).first()
        if complaint is not None:
            if job.status in {"ASSIGNED", "ACCEPTED", "ON_THE_WAY", "ARRIVED"}:
                target = "ASSIGNED"
            elif job.status == "IN_PROGRESS":
                target = "IN_PROGRESS"
            elif job.status == "COMPLETED":
                target = "RESOLVED" if complaint.status != "CLOSED" else "CLOSED"
            elif job.status == "CANCELLED":
                target = "CANCELLED"
            else:
                target = complaint.status

            updates = {"status": target, "updated_at": now}
            if complaint.company_id is None and job.company_id is not None:
                updates["company_id"] = job.company_id
            elif complaint.company_id not in (None, job.company_id):
                raise ValidationError("Complaint and job company ownership disagree.")
            if target == "RESOLVED" and complaint.resolved_date is None:
                updates["resolved_date"] = now
            if target not in {"RESOLVED", "CLOSED"}:
                updates["resolved_date"] = None
            Complaint.objects.filter(pk=complaint.pk).update(**updates)

    if job.job_type == "SERVICE":
        from service.models import Service

        service = Service.objects.filter(job=job).first()
        if service is not None:
            if job.status in {"ASSIGNED", "ACCEPTED", "ON_THE_WAY", "ARRIVED"}:
                target = "PENDING"
            elif job.status == "IN_PROGRESS":
                target = "IN_PROGRESS"
            elif job.status == "COMPLETED":
                target = "COMPLETED"
            elif job.status == "CANCELLED":
                target = "CANCELLED"
            else:
                target = service.status

            updates = {"status": target, "updated_at": now}
            if service.company_id is None and job.company_id is not None:
                updates["company_id"] = job.company_id
            elif service.company_id not in (None, job.company_id):
                raise ValidationError("Service and job company ownership disagree.")
            if target == "COMPLETED" and service.completed_date is None:
                updates["completed_date"] = now
            if target != "COMPLETED":
                updates["completed_date"] = None
            Service.objects.filter(pk=service.pk).update(**updates)
