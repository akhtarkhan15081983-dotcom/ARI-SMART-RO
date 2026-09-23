from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from complaints.models import Complaint
from service.models import Service
from .models import Job, JobPartUsed, JobActivityLog
from .services import NO_PARTS_ACTIVITY
from .workflow_sync import ensure_complaint_job, ensure_service_job, sync_sources_from_job


@receiver(pre_save, sender=Complaint)
def protect_complaint_completion(sender, instance, **kwargs):
    if instance.status not in {"RESOLVED", "CLOSED"}:
        return
    if instance.pk is None:
        raise ValidationError("Complaint cannot be created as resolved/closed; complete its secure Job workflow.")
    previous = Complaint.objects.filter(pk=instance.pk).only("status").first()
    if previous is not None and previous.status in {"RESOLVED", "CLOSED"}:
        return
    if not instance.job_id:
        raise ValidationError("Complaint must be completed through its secure Job workflow.")
    job_status = Job.objects.filter(pk=instance.job_id).values_list("status", flat=True).first()
    if job_status != "COMPLETED":
        raise ValidationError("Complaint must be completed through its secure Job workflow.")


@receiver(pre_save, sender=Service)
def protect_service_completion(sender, instance, **kwargs):
    if instance.status != "COMPLETED":
        return
    if instance.pk is None:
        raise ValidationError("Service cannot be created as completed; complete its secure Job workflow.")
    previous = Service.objects.filter(pk=instance.pk).only("status").first()
    if previous is not None and previous.status == "COMPLETED":
        return
    if not instance.job_id:
        raise ValidationError("Service must be completed through its secure Job workflow.")
    job_status = Job.objects.filter(pk=instance.job_id).values_list("status", flat=True).first()
    if job_status != "COMPLETED":
        raise ValidationError("Service must be completed through its secure Job workflow.")


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
        JobActivityLog.objects.filter(job=instance.job, activity=NO_PARTS_ACTIVITY).delete()
