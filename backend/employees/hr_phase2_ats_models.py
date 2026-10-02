from django.conf import settings
from django.db import models

from .hr_phase2_recruitment_models import CandidateApplication


class InterviewRound(models.Model):
    TYPE_CHOICES = [
        ("HR_SCREENING", "HR Screening"),
        ("TECHNICAL", "Technical"),
        ("MANAGERIAL", "Managerial"),
        ("PRACTICAL", "Practical"),
        ("FINAL", "Final"),
        ("OTHER", "Other"),
    ]
    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("NO_SHOW", "No Show"),
    ]

    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="interview_rounds")
    application = models.ForeignKey(CandidateApplication, on_delete=models.PROTECT, related_name="interview_rounds")
    round_number = models.PositiveSmallIntegerField()
    round_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    interviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assigned_interview_rounds")
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=160, blank=True, default="")
    meeting_reference = models.CharField(max_length=300, blank=True, default="")
    instructions = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="SCHEDULED")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_interview_rounds")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at", "round_number"]
        constraints = [
            models.UniqueConstraint(fields=["application", "round_number"], name="hr2_interview_application_round_uniq")
        ]
        indexes = [
            models.Index(fields=["company", "status", "scheduled_at"], name="hr2_int_company_status_idx"),
            models.Index(fields=["interviewer", "status"], name="hr2_int_interviewer_idx"),
        ]


class InterviewFeedback(models.Model):
    RECOMMENDATION_CHOICES = [
        ("STRONG_HIRE", "Strong Hire"),
        ("HIRE", "Hire"),
        ("HOLD", "Hold"),
        ("NO_HIRE", "No Hire"),
    ]

    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="interview_feedback")
    interview_round = models.ForeignKey(InterviewRound, on_delete=models.PROTECT, related_name="feedback_entries")
    interviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="interview_feedback_entries")
    rating = models.PositiveSmallIntegerField()
    recommendation = models.CharField(max_length=16, choices=RECOMMENDATION_CHOICES)
    strengths = models.TextField(blank=True, default="")
    concerns = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(fields=["interview_round", "interviewer"], name="hr2_feedback_round_interviewer_uniq")
        ]


class CandidateOffer(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("ISSUED", "Issued"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
        ("EXPIRED", "Expired"),
        ("WITHDRAWN", "Withdrawn"),
    ]

    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="candidate_offers")
    application = models.OneToOneField(CandidateApplication, on_delete=models.PROTECT, related_name="offer")
    job_title = models.CharField(max_length=120)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=20, blank=True, default="")
    employment_type = models.CharField(max_length=16)
    proposed_joining_date = models.DateField()
    work_location = models.CharField(max_length=120, blank=True, default="")
    compensation = models.DecimalField(max_digits=12, decimal_places=2)
    probation_terms = models.CharField(max_length=500, blank=True, default="")
    validity_date = models.DateField()
    hr_notes = models.TextField(blank=True, default="")
    approval_note = models.TextField(blank=True, default="")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="DRAFT")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_candidate_offers")
    approved_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    response_actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="recorded_candidate_offer_responses")
    response_note = models.TextField(blank=True, default="")
    response_evidence = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_candidate_offers")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "status"], name="hr2_offer_company_status_idx")]


class HrLetter(models.Model):
    TYPE_CHOICES = [
        ("OFFER", "Offer"),
        ("APPOINTMENT", "Appointment"),
        ("CONFIRMATION", "Confirmation"),
        ("PROMOTION", "Promotion"),
        ("INCREMENT", "Increment"),
        ("WARNING", "Warning"),
        ("NOTICE", "Notice"),
        ("SEPARATION", "Separation"),
    ]
    ACK_CHOICES = [("PENDING", "Pending"), ("ACKNOWLEDGED", "Acknowledged"), ("DECLINED", "Declined")]

    company = models.ForeignKey("tenancy.Company", on_delete=models.PROTECT, related_name="hr_letters")
    letter_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    candidate_offer = models.ForeignKey(CandidateOffer, on_delete=models.PROTECT, null=True, blank=True, related_name="letters")
    employee = models.ForeignKey("employees.EmployeeProfile", on_delete=models.PROTECT, null=True, blank=True, related_name="hr_letters")
    subject = models.CharField(max_length=200)
    snapshot = models.JSONField(default=dict)
    content_hash = models.CharField(max_length=64)
    version = models.PositiveSmallIntegerField(default=1)
    acknowledgement_status = models.CharField(max_length=16, choices=ACK_CHOICES, default="PENDING")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="issued_hr_letters")
    issued_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            models.UniqueConstraint(fields=["candidate_offer", "letter_type", "version"], name="hr2_letter_offer_type_version_uniq")
        ]
        indexes = [models.Index(fields=["company", "letter_type", "issued_at"], name="hr2_letter_company_type_idx")]
