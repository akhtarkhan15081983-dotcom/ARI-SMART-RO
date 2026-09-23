from django.db.models.signals import post_save
from django.dispatch import receiver

from complaints.models import Complaint
from service.models import Service
from .models import Job
from .workflow_sync import ensure_complaint_job, ensure_service_job, sync_sources_from_job


@receiver(post_save, sender=Complaint)
def complaint_saved(sender, instance, **kwargs):
    ensure_complaint_job(instance)


@receiver(post_save, sender=Service)
def service_saved(sender, instance, **kwargs):
    ensure_service_job(instance)


@receiver(post_save, sender=Job)
def job_saved(sender, instance, **kwargs):
    sync_sources_from_job(instance)
