from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .identifiers import allocate_operational_number


def _reserve(*, instance, field_name, namespace, model_label, prefix):
    if getattr(instance, field_name, None):
        return None
    year = timezone.now().year
    number = allocate_operational_number(
        namespace=namespace,
        model_label=model_label,
        field_name=field_name,
        prefix=prefix,
        year=year,
    )
    setattr(instance, field_name, f"{prefix}-{year}-{number:06d}")
    return year, number


@receiver(pre_save, sender="customers.Customer", dispatch_uid="tenancy.allocate_customer_id")
def allocate_customer_id(sender, instance, **kwargs):
    allocated = _reserve(
        instance=instance,
        field_name="customer_id",
        namespace="CUSTOMER",
        model_label="customers.Customer",
        prefix="CUS",
    )
    if allocated and not instance.card_number:
        year, number = allocated
        instance.card_number = f"ARI-{year}-{number:06d}"


@receiver(pre_save, sender="jobs.Job", dispatch_uid="tenancy.allocate_job_id")
def allocate_job_id(sender, instance, **kwargs):
    _reserve(
        instance=instance,
        field_name="job_id",
        namespace="JOB",
        model_label="jobs.Job",
        prefix="JOB",
    )


@receiver(pre_save, sender="service.Service", dispatch_uid="tenancy.allocate_service_id")
def allocate_service_id(sender, instance, **kwargs):
    _reserve(
        instance=instance,
        field_name="service_id",
        namespace="SERVICE",
        model_label="service.Service",
        prefix="SER",
    )


@receiver(pre_save, sender="complaints.Complaint", dispatch_uid="tenancy.allocate_complaint_id")
def allocate_complaint_id(sender, instance, **kwargs):
    _reserve(
        instance=instance,
        field_name="complaint_id",
        namespace="COMPLAINT",
        model_label="complaints.Complaint",
        prefix="CMP",
    )
