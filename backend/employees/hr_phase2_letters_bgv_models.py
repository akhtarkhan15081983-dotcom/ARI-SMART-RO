from django.conf import settings
from django.db import models
from django.db.models import Q

from .hr_phase2_ats_models import HrLetter
from .hr_phase2_recruitment_models import Candidate, CandidateApplication
from .models import EmployeeProfile


LETTER_TYPES = [
    ("APPOINTMENT", "Appointment"),
    ("CONFIRMATION", "Confirmation"),
    ("PROMOTION", "Promotion"),
    ("INCREMENT", "Increment"),
    ("WARNING", "Warning"),
    ("NOTICE", "Notice / Show Cause"),
    ("TRANSFER", "Transfer"),
    ("SEPARATION", "Separation / Relieving"),
    ("EXPERIENCE", "Experience"),
]


class HrLetterTemplate(models.Model):
    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="hr_letter_templates"
    )
    name = models.CharField(max_length=160)
    letter_type = models.CharField(max_length=20, choices=LETTER_TYPES)
    subject_template = models.CharField(max_length=200)
    body_template = models.TextField()
    version = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_hr_letter_templates"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_hr_letter_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["letter_type", "name", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name", "version"], name="hr2_letter_tpl_company_name_ver_uniq"
            )
        ]
        indexes = [
            models.Index(fields=["company", "letter_type", "is_active"], name="hr2_letter_tpl_company_idx")
        ]


class HrLetterWorkflow(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("ISSUED", "Issued"),
    ]

    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="hr_letter_workflows"
    )
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.PROTECT, related_name="hr_letter_workflows"
    )
    template = models.ForeignKey(
        HrLetterTemplate, on_delete=models.PROTECT, related_name="letter_workflows"
    )
    letter_type = models.CharField(max_length=20, choices=LETTER_TYPES)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    effective_date = models.DateField()
    context = models.JSONField(default=dict, blank=True)
    lifecycle_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    career_movement_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="DRAFT")
    approval_note = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="approved_hr_letter_workflows"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    issued_letter = models.OneToOneField(
        HrLetter, on_delete=models.PROTECT, null=True, blank=True,
        related_name="workflow_source"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_hr_letter_workflows"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "status", "letter_type"], name="hr2_letter_flow_company_idx"),
            models.Index(fields=["employee", "status"], name="hr2_letter_flow_employee_idx"),
        ]


class HrLetterAcknowledgement(models.Model):
    letter = models.OneToOneField(
        HrLetter, on_delete=models.PROTECT, related_name="acknowledgement"
    )
    status = models.CharField(max_length=16, choices=HrLetter.ACK_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hr_letter_acknowledgements"
    )
    note = models.TextField(blank=True, default="")
    evidence = models.JSONField(default=dict, blank=True)
    responded_at = models.DateTimeField(auto_now_add=True)


class BgvPolicy(models.Model):
    company = models.OneToOneField(
        "tenancy.Company", on_delete=models.PROTECT, related_name="bgv_policy"
    )
    mandatory_before_ready = models.BooleanField(default=False)
    required_checks = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_bgv_policies"
    )
    updated_at = models.DateTimeField(auto_now=True)


class BackgroundVerificationCase(models.Model):
    STATUS_CHOICES = [
        ("NOT_STARTED", "Not Started"),
        ("IN_PROGRESS", "In Progress"),
        ("CLEAR", "Clear"),
        ("CONDITIONAL", "Conditional"),
        ("FAILED", "Failed"),
        ("WAIVED", "Waived"),
    ]

    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="bgv_cases"
    )
    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, null=True, blank=True, related_name="bgv_cases"
    )
    application = models.ForeignKey(
        CandidateApplication, on_delete=models.PROTECT, null=True, blank=True, related_name="bgv_cases"
    )
    employee = models.ForeignKey(
        EmployeeProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="bgv_cases"
    )
    overall_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOT_STARTED")
    decision_note = models.TextField(blank=True, default="")
    waiver_reason = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="decided_bgv_cases"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_bgv_cases"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(candidate__isnull=False) | Q(employee__isnull=False),
                name="hr2_bgv_case_has_subject",
            ),
            models.UniqueConstraint(
                fields=["application"], condition=Q(application__isnull=False),
                name="hr2_bgv_unique_application"
            ),
            models.UniqueConstraint(
                fields=["employee"], condition=Q(employee__isnull=False),
                name="hr2_bgv_unique_employee"
            ),
        ]
        indexes = [
            models.Index(fields=["company", "overall_status"], name="hr2_bgv_company_status_idx")
        ]


class BackgroundVerificationCheck(models.Model):
    TYPE_CHOICES = [
        ("IDENTITY", "Identity"),
        ("ADDRESS", "Address"),
        ("EDUCATION", "Education"),
        ("EMPLOYMENT", "Previous Employment"),
        ("CRIMINAL_POLICE", "Criminal / Police"),
        ("REFERENCE", "Reference Check"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("VERIFIED", "Verified"),
        ("FAILED", "Failed"),
        ("NOT_APPLICABLE", "Not Applicable"),
    ]

    case = models.ForeignKey(
        BackgroundVerificationCase, on_delete=models.PROTECT, related_name="checks"
    )
    check_type = models.CharField(max_length=24, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    details = models.JSONField(default=dict, blank=True)
    evidence_reference = models.CharField(max_length=300, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="bgv_checks_verified"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["check_type"]
        constraints = [
            models.UniqueConstraint(fields=["case", "check_type"], name="hr2_bgv_case_check_type_uniq")
        ]
        indexes = [models.Index(fields=["case", "status"], name="hr2_bgv_check_case_status_idx")]


class CorporateHrAuditEvent(models.Model):
    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="corporate_hr_audit_events"
    )
    entity_type = models.CharField(max_length=40)
    entity_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=40, blank=True, default="")
    to_status = models.CharField(max_length=40, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="corporate_hr_audit_events"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "entity_type", "entity_id"], name="hr2_corp_audit_entity_idx")
        ]
