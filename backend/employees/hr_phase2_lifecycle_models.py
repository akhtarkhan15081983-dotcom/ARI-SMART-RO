from django.conf import settings
from django.db import models

from .models import EmployeeProfile


class EmployeeLifecycleAction(models.Model):
    ACTION_TYPES = [
        ("PROBATION_REVIEW", "Probation Review"), ("PROBATION_EXTENSION", "Probation Extension"),
        ("CONFIRMATION", "Confirmation"), ("PROMOTION", "Promotion"), ("INCREMENT", "Increment"),
        ("TRANSFER", "Transfer"), ("SEPARATION", "Separation"),
    ]
    STATUS_CHOICES = [
        ("DRAFT", "Draft"), ("MANAGER_REVIEW", "Manager Review"), ("HR_REVIEW", "HR Review"),
        ("PENDING_APPROVAL", "Pending Approval"), ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"), ("APPLIED", "Applied"), ("CANCELLED", "Cancelled"),
    ]
    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="employee_lifecycle_actions")
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name="phase2_lifecycle_actions")
    action_type = models.CharField(max_length=24, choices=ACTION_TYPES)
    effective_date = models.DateField()
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="DRAFT")
    reason = models.TextField()
    proposed_changes = models.JSONField(default=dict, blank=True)
    snapshot_before = models.JSONField(default=dict, blank=True)
    manager_assessment = models.JSONField(default=dict, blank=True)
    hr_assessment = models.JSONField(default=dict, blank=True)
    manager_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="manager_reviewed_lifecycle_actions")
    manager_reviewed_at = models.DateTimeField(null=True, blank=True)
    hr_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="hr_reviewed_lifecycle_actions")
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_employee_lifecycle_actions")
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    career_movement_id = models.PositiveBigIntegerField(null=True, blank=True)
    letter_workflow_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_employee_lifecycle_actions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        indexes = [models.Index(fields=["company", "status", "action_type"], name="hr2_life_company_queue_idx"), models.Index(fields=["employee", "effective_date"], name="hr2_life_employee_date_idx")]


class ExitCase(models.Model):
    SEPARATION_TYPES = [("RESIGNATION", "Resignation"), ("TERMINATION", "Termination"), ("RETIREMENT", "Retirement"), ("CONTRACT_COMPLETION", "Contract Completion"), ("ABSCONDING", "Absconding")]
    STATUS_CHOICES = [("DRAFT", "Draft"), ("NOTICE", "Notice"), ("CLEARANCE", "Clearance"), ("PENDING_APPROVAL", "Pending Approval"), ("APPROVED", "Approved"), ("SEPARATED", "Separated"), ("CANCELLED", "Cancelled")]
    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="employee_exit_cases")
    employee = models.OneToOneField(EmployeeProfile, on_delete=models.PROTECT, related_name="phase2_exit_case")
    separation_type = models.CharField(max_length=24, choices=SEPARATION_TYPES)
    resignation_date = models.DateField(null=True, blank=True)
    notice_days = models.PositiveSmallIntegerField(default=0)
    proposed_last_working_date = models.DateField()
    approved_last_working_date = models.DateField(null=True, blank=True)
    notice_waiver_days = models.PositiveSmallIntegerField(default=0)
    notice_recovery_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.TextField()
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="DRAFT")
    final_settlement_ready = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_exit_cases")
    approved_at = models.DateTimeField(null=True, blank=True)
    separated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_exit_cases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["company", "status"], name="hr2_exit_company_status_idx")]


class ExitClearance(models.Model):
    CLEARANCE_TYPES = [("ASSET", "Company Assets"), ("FINANCE", "Finance / Payroll"), ("MANAGER", "Manager"), ("HR", "HR")]
    STATUS_CHOICES = [("PENDING", "Pending"), ("CLEARED", "Cleared"), ("BLOCKED", "Blocked"), ("WAIVED", "Waived")]
    exit_case = models.ForeignKey(ExitCase, on_delete=models.PROTECT, related_name="clearances")
    clearance_type = models.CharField(max_length=16, choices=CLEARANCE_TYPES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    note = models.TextField(blank=True, default="")
    evidence = models.JSONField(default=dict, blank=True)
    waiver_reason = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_exit_clearances")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["exit_case", "clearance_type"], name="hr2_exit_clearance_type_uniq")]


class EmployeeLifecycleAudit(models.Model):
    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="employee_lifecycle_audits")
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name="phase2_lifecycle_audits")
    entity_type = models.CharField(max_length=30)
    entity_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="employee_lifecycle_audits")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "employee", "created_at"], name="hr2_life_audit_emp_idx")]
