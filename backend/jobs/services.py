from django.utils import timezone

from .models import JobActivityLog


def accept_job(job):

    if job.status != "ASSIGNED":
        raise ValueError(
            f"Job cannot be accepted because its current status is '{job.status}'."
        )

    job.status = "ACCEPTED"
    job.accepted_at = timezone.now()
    job.save()

    JobActivityLog.objects.create(
        job=job,
        engineer=job.engineer,
        activity="Job Accepted"
    )

    return job

STATUS_CONFIG = {
    "ACCEPTED": {
        "current": ["ASSIGNED"],
        "time_field": "accepted_at",
        "activity": "Job Accepted",
    },
    "ON_THE_WAY": {
        "current": ["ACCEPTED"],
        "time_field": "on_the_way_at",
        "activity": "Engineer Started Journey",
    },
    "ARRIVED": {
        "current": ["ON_THE_WAY"],
        "time_field": "arrived_at",
        "activity": "Engineer Arrived",
    },
    "IN_PROGRESS": {
        "current": ["ARRIVED"],
        "time_field": "in_progress_at",
        "activity": "Work Started",
    },
    "COMPLETED": {
        "current": ["IN_PROGRESS"],
        "time_field": "completed_at",
        "activity": "Job Completed",
    },
}
    

def change_job_status(job, new_status):

    if new_status not in STATUS_CONFIG:
        raise ValueError("Invalid status.")

    config = STATUS_CONFIG[new_status]

    if new_status == "COMPLETED":

        if not job.parts_used.exists():
            raise ValueError(
                "Cannot complete job: parts have not been scanned."
            )

        if not hasattr(job, "installation"):
            raise ValueError(
                "Cannot complete job: installation details are missing."
            )

        if not job.media.filter(
            media_type="PHOTO",
            description="After Photo",
        ).exists():
            raise ValueError(
                "Cannot complete job: after photo is missing."
            )

        if not job.otp_verified:
            raise ValueError(
                "Cannot complete job: customer OTP is not verified."
            )

        if not hasattr(job, "signature"):
            raise ValueError(
                "Cannot complete job: customer signature is missing."
            )

    if job.status not in config["current"]:
        raise ValueError(
            f"Cannot change status from '{job.status}' to '{new_status}'."
        )

    job.status = new_status

    if "time_field" in config:
        setattr(job, config["time_field"], timezone.now())

    job.save()

    JobActivityLog.objects.create(
        job=job,
        engineer=job.engineer,
        activity=config["activity"],
    )

    return job