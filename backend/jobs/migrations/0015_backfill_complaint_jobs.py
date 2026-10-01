from django.db import migrations
from django.utils import timezone


PRIORITY_MAP = {
    "NORMAL": "MEDIUM",
    "URGENT": "HIGH",
    "EMERGENCY": "HIGH",
}


def _next_job_number(Job, year):
    prefix = f"JOB-{year}-"
    highest = 0
    for value in Job.objects.filter(job_id__startswith=prefix).values_list("job_id", flat=True):
        try:
            highest = max(highest, int(str(value).rsplit("-", 1)[-1]))
        except (TypeError, ValueError):
            continue
    return highest + 1


def backfill_complaint_jobs(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    Job = apps.get_model("jobs", "Job")
    ROAsset = apps.get_model("assets", "ROAsset")

    complaints = Complaint.objects.filter(
        engineer__isnull=False,
        job__isnull=True,
    ).exclude(status__in=["CLOSED", "CANCELLED"])

    # Data migrations use Django's historical model and therefore do not run
    # Job.save(), which normally assigns JOB-YYYY-NNNNNN. Allocate IDs here so
    # a second backfilled complaint never collides on the unique blank job_id.
    next_numbers = {}

    for complaint in complaints.iterator():
        scheduled = (
            complaint.scheduled_date
            or complaint.complaint_date
            or timezone.now()
        )
        year = scheduled.year
        if year not in next_numbers:
            next_numbers[year] = _next_job_number(Job, year)
        number = next_numbers[year]
        next_numbers[year] += 1
        job_id = f"JOB-{year}-{number:06d}"

        # Be defensive if hand-created/imported IDs leave a gap race in the
        # sequence. This migration is single-process, so advance until free.
        while Job.objects.filter(job_id=job_id).exists():
            number = next_numbers[year]
            next_numbers[year] += 1
            job_id = f"JOB-{year}-{number:06d}"

        asset = (
            ROAsset.objects
            .filter(current_customer_id=complaint.customer_id, is_active=True)
            .order_by("-id")
            .first()
        )

        job = Job.objects.create(
            job_id=job_id,
            customer_id=complaint.customer_id,
            ro_asset_id=asset.id if asset else None,
            engineer_id=complaint.engineer_id,
            job_type="COMPLAINT",
            priority=PRIORITY_MAP.get(complaint.priority, "MEDIUM"),
            scheduled_date=scheduled,
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
