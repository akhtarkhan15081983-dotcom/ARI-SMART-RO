from django.conf import settings
from django.db import models
from django.utils import timezone


class ManpowerRequisition(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CLOSED", "Closed"),
    ]

    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="manpower_requisitions"
    )
    department = models.CharField(max_length=100)
    job_title = models.CharField(max_length=120)
    designation = models.CharField(max_length=20, blank=True, default="")
    positions = models.PositiveSmallIntegerField(default=1)
    employment_type = models.CharField(max_length=16, default="PROBATION")
    location = models.CharField(max_length=120, blank=True, default="")
    target_joining_date = models.DateField(null=True, blank=True)
    justification = models.TextField()
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="DRAFT")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_manpower"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="approved_manpower"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="hr2_req_company_status_idx"),
            models.Index(fields=["company", "department"], name="hr2_req_company_dept_idx"),
        ]


class JobOpening(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("OPEN", "Open"),
        ("ON_HOLD", "On Hold"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    ]

    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="job_openings"
    )
    requisition = models.OneToOneField(
        ManpowerRequisition, on_delete=models.PROTECT, related_name="job_opening"
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    requirements = models.TextField(blank=True, default="")
    vacancies = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="DRAFT")
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_job_openings"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "status"], name="hr2_job_company_status_idx")]


class Candidate(models.Model):
    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="hr_candidates"
    )
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    current_company = models.CharField(max_length=160, blank=True, default="")
    current_title = models.CharField(max_length=120, blank=True, default="")
    experience_years = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    source = models.CharField(max_length=80, blank=True, default="")
    resume = models.FileField(upload_to="employees/recruitment/resumes/", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_hr_candidates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "phone"], name="hr2_candidate_company_phone_uniq")
        ]
        indexes = [models.Index(fields=["company", "full_name"], name="hr2_candidate_company_name_idx")]


class CandidateApplication(models.Model):
    STAGE_CHOICES = [
        ("APPLIED", "Applied"),
        ("SCREENING", "Screening"),
        ("INTERVIEW", "Interview"),
        ("SELECTED", "Selected"),
        ("REJECTED", "Rejected"),
        ("OFFERED", "Offered"),
        ("JOINED", "Joined"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="candidate_applications"
    )
    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name="applications")
    job_opening = models.ForeignKey(JobOpening, on_delete=models.PROTECT, related_name="applications")
    stage = models.CharField(max_length=16, choices=STAGE_CHOICES, default="APPLIED")
    expected_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    available_from = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    rejection_reason = models.CharField(max_length=500, blank=True, default="")
    converted_employee = models.OneToOneField(
        "employees.EmployeeProfile", on_delete=models.PROTECT, null=True, blank=True,
        related_name="source_candidate_application"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_candidate_applications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job_opening"], name="hr2_candidate_job_application_uniq"
            )
        ]
        indexes = [
            models.Index(fields=["company", "stage"], name="hr2_app_company_stage_idx"),
            models.Index(fields=["job_opening", "stage"], name="hr2_app_job_stage_idx"),
        ]


class RecruitmentAuditEvent(models.Model):
    company = models.ForeignKey(
        "tenancy.Company", on_delete=models.PROTECT, related_name="recruitment_audit_events"
    )
    entity_type = models.CharField(max_length=40)
    entity_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=40, blank=True, default="")
    to_status = models.CharField(max_length=40, blank=True, default="")
    reason = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recruitment_audit_events"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "entity_type", "entity_id"], name="hr2_audit_entity_idx")
        ]
