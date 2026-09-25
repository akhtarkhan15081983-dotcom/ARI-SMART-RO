from django.db import migrations
from django.utils import timezone


PRIORITY_MAP = {
    "NORMAL": "MEDIUM",
    "URGENT": "HIGH",
    "EMERGENCY": "HIGH",
}


def backfill_complaint_jobs(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    Job = apps.get_model("jobs", "Job")
    ROAsset = apps.get_model("assets", "ROAsset")

    complaints = Complaint.objects.filter(
        engineer__isnull=False,
        job__isnull=True,
    ).exclude(status__in=["CLOSED", "CANCELLED"])

    for complaint in complaints.iterator():
        asset = (
            ROAsset.objects
            .filter(current_customer_id=complaint.customer_id, is_active=True)
            .order_by("-id")
            .first()
        )

        job = Job.objects.create(
            customer_id=complaint.customer_id,
            ro_asset_id=asset.id if asset else None,
            engineer_id=complaint.engineer_id,
            job_type="COMPLAINT",
            priority=PRIORITY_MAP.get(complaint.priority, "MEDIUM"),
            scheduled_date=(
                complaint.scheduled_date
                or complaint.complaint_date
                or timezone.now()
            ),
            status="ASSIGNED",
            remarks=complaint.description or complaint.complaint_id,
        )
        Complaint.objects.filter(pk=complaint.pk).update(job_id=job.id)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0014_alter_job_ro_asset_nullable"),
        ("complaints", "0003_repair_assigned_complaint_status"),
    ]

    operations = [
        migrations.RunPython(backfill_complaint_jobs, noop),
    ]
