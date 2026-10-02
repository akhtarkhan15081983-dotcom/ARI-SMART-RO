from calendar import monthrange

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class EmployeeHrLifecycle(models.Model):
    EMPLOYMENT_TYPES = [
        ("PROBATION", "Probation"),
        ("PERMANENT", "Permanent"),
        ("CONTRACT", "Contract"),
        ("TRAINEE", "Trainee"),
    ]
    EMPLOYMENT_STATUSES = [
        ("ONBOARDING", "Onboarding"),
        ("PROBATION", "Probation"),
        ("CONFIRMED", "Confirmed"),
        ("NOTICE", "Notice Period"),
        ("SUSPENDED", "Suspended"),
        ("SEPARATED", "Separated"),
        ("INACTIVE", "Inactive"),
    ]
    HR_STAGES = [
        ("CREATED", "Created"),
        ("PROFILE_PENDING", "Profile Pending"),
        ("DOCUMENT_PENDING", "Document Pending"),
        ("SECURITY_PENDING", "Security Pending"),
        ("TRAINING_PENDING", "Training Pending"),
        ("HR_REVIEW", "HR Review"),
        ("READY", "Ready for Duty"),
    ]

    employee = models.OneToOneField(
        "employees.EmployeeProfile",
        on_delete=models.CASCADE,
        related_name="hr_lifecycle",
    )
    employment_type = models.CharField(max_length=16, choices=EMPLOYMENT_TYPES, default="PROBATION")
    employment_status = models.CharField(max_length=16, choices=EMPLOYMENT_STATUSES, default="ONBOARDING")
    hr_stage = models.CharField(max_length=24, choices=HR_STAGES, default="CREATED")
    work_location = models.CharField(max_length=120, blank=True, default="")
    probation_months = models.PositiveSmallIntegerField(default=3)
    probation_start_date = models.DateField(null=True, blank=True)
    confirmation_due_date = models.DateField(null=True, blank=True)
    confirmed_at = models.DateField(null=True, blank=True)
    manager_review_status = models.CharField(max_length=16, default="PENDING")
    manager_review_note = models.TextField(blank=True, default="")
    hr_review_status = models.CharField(max_length=16, default="PENDING")
    hr_review_note = models.TextField(blank=True, default="")
    policy_acknowledged = models.BooleanField(default=False)
    sop_acknowledged = models.BooleanField(default=False)
    safety_training_acknowledged = models.BooleanField(default=False)
    payroll_details_complete = models.BooleanField(default=False)
    role_access_assigned = models.BooleanField(default=False)
    joining_checklist = models.JSONField(default=dict, blank=True)
    bank_details = models.JSONField(default=dict, blank=True)
    compensation_profile = models.JSONField(default=dict, blank=True)
    hr_override_ready = models.BooleanField(default=False)
    hr_override_reason = models.CharField(max_length=500, blank=True, default="")
    notice_start_date = models.DateField(null=True, blank=True)
    last_working_date = models.DateField(null=True, blank=True)
    separation_type = models.CharField(max_length=40, blank=True, default="")
    exit_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee__employee_id"]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.employment_status}"


class EmployeeHrLifecycleEvent(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.PROTECT,
        related_name="hr_lifecycle_events",
    )
    event_type = models.CharField(max_length=40)
    effective_date = models.DateField(default=timezone.localdate)
    from_status = models.CharField(max_length=40, blank=True, default="")
    to_status = models.CharField(max_length=40, blank=True, default="")
    note = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_hr_lifecycle_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.event_type}"


def _add_months(value, months):
    total = value.year * 12 + (value.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@receiver(post_save, sender="employees.EmployeeProfile")
def ensure_hr_lifecycle(sender, instance, created, **kwargs):
    """Every employee gets a durable HR lifecycle record without changing legacy APIs."""
    if not created:
        return
    start = instance.joining_date or timezone.localdate()
    EmployeeHrLifecycle.objects.get_or_create(
        employee=instance,
        defaults={
            "employment_type": "PROBATION",
            "employment_status": "ONBOARDING",
            "hr_stage": "CREATED",
            "probation_start_date": start,
            "confirmation_due_date": _add_months(start, 3),
        },
    )
