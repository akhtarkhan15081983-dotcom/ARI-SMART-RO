from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from rest_framework.exceptions import ValidationError

from complaints.models import Complaint
from service.models import Service
from .models import Job, JobPartUsed, JobActivityLog
from .services import NO_PARTS_ACTIVITY
from .workflow_sync import ensure_complaint_job, ensure_service_job, sync_sources_from_job


def _job_status(job_id):
    if not job_id:
        return None
    return Job.objects.filter(pk=job_id).values_list("status", flat=True).first()


@receiver(pre_save, sender=Complaint)
def protect_complaint_execution(sender, instance, **kwargs):
    if instance.pk is None:
        if instance.status in {"IN_PROGRESS", "RESOLVED", "CLOSED"}:
            raise ValidationError(
                "Complaint field work must run through its secure Job workflow."
            )
        return

    previous = Complaint.objects.filter(pk=instance.pk).only("status").first()
    if previous is None or previous.status == instance.status:
        return

    job_status = _job_status(instance.job_id)
    if instance.status == "IN_PROGRESS" and job_status != "IN_PROGRESS":
        raise ValidationError(
            "Start this complaint from the linked secure Job workflow."
        )
    if instance.status in {"RESOLVED", "CLOSED"}:
        if previous.status in {"RESOLVED", "CLOSED"}:
            return
        if job_status != "COMPLETED":
            raise ValidationError(
                "Complaint must be completed through its secure Job workflow."
            )


@receiver(pre_save, sender=Service)
def protect_service_execution(sender, instance, **kwargs):
    if instance.pk is None:
        if instance.status in {"IN_PROGRESS", "COMPLETED"}:
            raise ValidationError(
                "Service field work must run through its secure Job workflow."
            )
        return

    previous = Service.objects.filter(pk=instance.pk).only("status").first()
    if previous is None or previous.status == instance.status:
        return

    job_status = _job_status(instance.job_id)
    if instance.status == "IN_PROGRESS" and job_status != "IN_PROGRESS":
        raise ValidationError(
            "Start this service from the linked secure Job workflow."
        )
    if instance.status == "COMPLETED" and job_status != "COMPLETED":
        raise ValidationError(
            "Service must be completed through its secure Job workflow."
        )


@receiver(post_save, sender=Complaint)
def complaint_saved(sender, instance, **kwargs):
    ensure_complaint_job(instance)


@receiver(post_save, sender=Service)
def service_saved(sender, instance, **kwargs):
    ensure_service_job(instance)


@receiver(post_save, sender=Job)
def job_saved(sender, instance, **kwargs):
    sync_sources_from_job(instance)


@receiver(post_save, sender=JobPartUsed)
def invalidate_no_parts_declaration(sender, instance, created, **kwargs):
    if created:
        JobActivityLog.objects.filter(
            job=instance.job,
            activity=NO_PARTS_ACTIVITY,
        ).delete()
