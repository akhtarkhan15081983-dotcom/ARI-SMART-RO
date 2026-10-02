from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership

from .hr_lifecycle_models import EmployeeHrLifecycle
from .hr_phase2_ats_models import CandidateOffer, HrLetter, InterviewFeedback, InterviewRound
from .hr_phase2_recruitment_models import Candidate, CandidateApplication, JobOpening, ManpowerRequisition, RecruitmentAuditEvent
from .models import EmployeeProfile


class CorporateHrPhase2AtsTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ATS Tenant", slug="ats-tenant", phone="9444444400",
            is_active=True, lifecycle_status="ACTIVE",
        )
        self.other_company = Company.objects.create(
            name="ATS Other", slug="ats-other", phone="9444444490",
            is_active=True, lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9444444401", password="Strong@Test1", role="ADMIN",
            first_name="HR", last_name="Admin", is_verified=True,
        )
        self.office = User.objects.create_user(
            phone="9444444402", password="Strong@Test1", role="OFFICE",
            first_name="Recruitment", last_name="Officer", is_verified=True,
        )
        self.interviewer = User.objects.create_user(
            phone="9444444403", password="Strong@Test1", role="MANAGER",
            first_name="Hiring", last_name="Manager", is_verified=True,
        )
        self.other_manager = User.objects.create_user(
            phone="9444444404", password="Strong@Test1", role="MANAGER",
            first_name="Other", last_name="Manager", is_verified=True,
        )
        self.foreign_admin = User.objects.create_user(
            phone="9444444491", password="Strong@Test1", role="ADMIN",
            first_name="Foreign", last_name="Admin", is_verified=True,
        )
        CompanyMembership.objects.create(company=self.company, user=self.admin, role="OWNER", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.office, role="STAFF", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.interviewer, role="MANAGER", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.other_manager, role="MANAGER", is_active=True)
        CompanyMembership.objects.create(company=self.other_company, user=self.foreign_admin, role="OWNER", is_active=True)

        self.req = ManpowerRequisition.objects.create(
            company=self.company, department="Service", job_title="Service Engineer",
            designation="ENGINEER", positions=1, employment_type="PROBATION",
            location="Mathura", justification="Approved hiring need", status="APPROVED",
            requested_by=self.office, approved_by=self.admin, approved_at=timezone.now(),
        )
        self.job = JobOpening.objects.create(
            company=self.company, requisition=self.req, title="Service Engineer",
            vacancies=1, status="OPEN", opened_at=timezone.now(), created_by=self.office,
        )
        self.candidate = Candidate.objects.create(
            company=self.company, full_name="Ravi Kumar", phone="9777777701",
            email="ravi@example.com", created_by=self.office,
        )
        self.application = CandidateApplication.objects.create(
            company=self.company, candidate=self.candidate, job_opening=self.job,
            stage="SCREENING", created_by=self.office,
        )
        self.interviews = "/api/employees/hrms/recruitment/interviews/"
        self.offers = "/api/employees/hrms/recruitment/offers/"
        self.summary = "/api/employees/hrms/recruitment/summary/"

    def _schedule(self, interviewer=None, application=None):
        self.client.force_authenticate(self.office)
        response = self.client.post(self.interviews, {
            "application_id": (application or self.application).id,
            "round_number": 1,
            "round_type": "MANAGERIAL",
            "interviewer_id": (interviewer or self.interviewer).id,
            "scheduled_at": (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
            "location": "Head Office",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return InterviewRound.objects.get(pk=response.data["id"])

    def _complete_interview(self):
        interview = self._schedule()
        self.client.force_authenticate(self.interviewer)
        feedback = self.client.post(f"{self.interviews}{interview.id}/feedback/", {
            "rating": 5, "recommendation": "HIRE", "strengths": "Strong field knowledge",
            "concerns": "", "notes": "Recommended",
        }, format="json")
        self.assertEqual(feedback.status_code, 201)
        complete = self.client.post(f"{self.interviews}{interview.id}/action/", {"action": "COMPLETE"}, format="json")
        self.assertEqual(complete.status_code, 200)
        return interview

    def _select(self):
        if self.application.stage != "INTERVIEW":
            self.application.stage = "INTERVIEW"
            self.application.save(update_fields=["stage", "updated_at"])
        if not self.application.interview_rounds.filter(status="COMPLETED").exists():
            self._complete_interview()
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/",
            {"action": "SELECT", "reason": "Approved after interview panel review."}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.stage, "SELECTED")

    def _issue_and_accept_offer(self):
        self._select()
        self.client.force_authenticate(self.office)
        created = self.client.post(self.offers, {
            "application_id": self.application.id,
            "proposed_joining_date": (timezone.localdate() + timezone.timedelta(days=7)).isoformat(),
            "validity_date": (timezone.localdate() + timezone.timedelta(days=5)).isoformat(),
            "compensation": "28000",
            "probation_terms": "Three months probation",
        }, format="json")
        self.assertEqual(created.status_code, 201)
        offer_id = created.data["id"]
        submitted = self.client.post(f"{self.offers}{offer_id}/action/", {"action": "SUBMIT"}, format="json")
        self.assertEqual(submitted.status_code, 200)
        self.client.force_authenticate(self.admin)
        approved = self.client.post(f"{self.offers}{offer_id}/action/", {"action": "APPROVE", "reason": "Budget approved"}, format="json")
        self.assertEqual(approved.status_code, 200)
        self.client.force_authenticate(self.office)
        issued = self.client.post(f"{self.offers}{offer_id}/action/", {"action": "ISSUE"}, format="json")
        self.assertEqual(issued.status_code, 200)
        accepted = self.client.post(f"{self.offers}{offer_id}/action/", {"action": "ACCEPT", "reason": "Candidate confirmed by phone"}, format="json")
        self.assertEqual(accepted.status_code, 200)
        return CandidateOffer.objects.get(pk=offer_id)

    def test_interview_tenant_assignment_visibility_and_feedback_immutability(self):
        self.client.force_authenticate(self.office)
        foreign = self.client.post(self.interviews, {
            "application_id": self.application.id, "round_number": 1,
            "round_type": "MANAGERIAL", "interviewer_id": self.foreign_admin.id,
            "scheduled_at": (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
        }, format="json")
        self.assertEqual(foreign.status_code, 400)

        interview = self._schedule()
        self.client.force_authenticate(self.other_manager)
        invisible = self.client.get(self.interviews)
        self.assertEqual(invisible.status_code, 200)
        self.assertEqual(invisible.data["interviews"], [])
        denied = self.client.post(f"{self.interviews}{interview.id}/feedback/", {"rating": 4, "recommendation": "HIRE"}, format="json")
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.interviewer)
        first = self.client.post(f"{self.interviews}{interview.id}/feedback/", {"rating": 4, "recommendation": "HIRE"}, format="json")
        self.assertEqual(first.status_code, 201)
        duplicate = self.client.post(f"{self.interviews}{interview.id}/feedback/", {"rating": 5, "recommendation": "STRONG_HIRE"}, format="json")
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(InterviewFeedback.objects.filter(interview_round=interview).count(), 1)

    def test_interview_completion_requires_feedback_and_cancel_requires_reason(self):
        interview = self._schedule()
        self.client.force_authenticate(self.interviewer)
        blocked = self.client.post(f"{self.interviews}{interview.id}/action/", {"action": "COMPLETE"}, format="json")
        self.assertEqual(blocked.status_code, 400)
        no_reason = self.client.post(f"{self.interviews}{interview.id}/action/", {"action": "CANCEL"}, format="json")
        self.assertEqual(no_reason.status_code, 400)

    def test_selection_requires_approver_note_and_completed_interview(self):
        self.application.stage = "INTERVIEW"
        self.application.save(update_fields=["stage", "updated_at"])
        self.client.force_authenticate(self.admin)
        no_note = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/", {"action": "SELECT"}, format="json")
        self.assertEqual(no_note.status_code, 400)
        no_interview = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/", {"action": "SELECT", "reason": "Approve"}, format="json")
        self.assertEqual(no_interview.status_code, 400)
        self._complete_interview()
        self.client.force_authenticate(self.admin)
        selected = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/", {"action": "SELECT", "reason": "Panel approved"}, format="json")
        self.assertEqual(selected.status_code, 200)

    def test_rejection_requires_reason_and_reopen_is_audited(self):
        self.application.stage = "INTERVIEW"
        self.application.save(update_fields=["stage", "updated_at"])
        self.client.force_authenticate(self.admin)
        missing = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/", {"action": "REJECT"}, format="json")
        self.assertEqual(missing.status_code, 400)
        rejected = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/", {"action": "REJECT", "reason": "Experience mismatch"}, format="json")
        self.assertEqual(rejected.status_code, 200)
        reopened = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/decision/", {"action": "REOPEN", "reason": "Additional experience evidence received"}, format="json")
        self.assertEqual(reopened.status_code, 200)
        self.assertTrue(RecruitmentAuditEvent.objects.filter(entity_type="CANDIDATE_APPLICATION", entity_id=self.application.id, action="REOPEN").exists())

    def test_offer_requires_selection_and_issued_letter_snapshot_is_immutable(self):
        self.client.force_authenticate(self.office)
        blocked = self.client.post(self.offers, {
            "application_id": self.application.id,
            "proposed_joining_date": (timezone.localdate() + timezone.timedelta(days=7)).isoformat(),
            "validity_date": (timezone.localdate() + timezone.timedelta(days=5)).isoformat(),
            "compensation": "28000",
        }, format="json")
        self.assertEqual(blocked.status_code, 400)
        offer = self._issue_and_accept_offer()
        letter = HrLetter.objects.get(candidate_offer=offer, letter_type="OFFER")
        original_snapshot = dict(letter.snapshot)
        original_hash = letter.content_hash
        self.candidate.full_name = "Changed Candidate Name"
        self.candidate.save(update_fields=["full_name", "updated_at"])
        letter.refresh_from_db()
        self.assertEqual(letter.snapshot, original_snapshot)
        self.assertEqual(letter.content_hash, original_hash)

    def test_conversion_is_atomic_idempotent_and_preserves_onboarding(self):
        offer = self._issue_and_accept_offer()
        self.client.force_authenticate(self.admin)
        converted = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/convert/", {}, format="json")
        self.assertEqual(converted.status_code, 201)
        employee_id = converted.data["employee_id"]
        user_count = User.objects.filter(phone=self.candidate.phone).count()
        employee_count = EmployeeProfile.objects.filter(pk=employee_id).count()

        repeated = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/convert/", {}, format="json")
        self.assertEqual(repeated.status_code, 200)
        self.assertTrue(repeated.data["idempotent"])
        self.assertEqual(repeated.data["employee_id"], employee_id)
        self.assertEqual(User.objects.filter(phone=self.candidate.phone).count(), user_count)
        self.assertEqual(EmployeeProfile.objects.filter(pk=employee_id).count(), employee_count)
        employee = EmployeeProfile.objects.get(pk=employee_id)
        lifecycle = EmployeeHrLifecycle.objects.get(employee=employee)
        self.assertEqual(lifecycle.employment_status, "ONBOARDING")
        self.assertEqual(lifecycle.hr_stage, "CREATED")
        self.assertEqual(lifecycle.employment_type, "PROBATION")
        self.assertEqual(lifecycle.work_location, "Mathura")

    def test_customer_account_is_not_silently_reused(self):
        User.objects.create_user(
            phone=self.candidate.phone, password="Customer@Test1", role="CUSTOMER",
            first_name="Existing", last_name="Customer", is_verified=True,
        )
        self._issue_and_accept_offer()
        self.client.force_authenticate(self.admin)
        blocked = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/convert/", {}, format="json")
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(EmployeeProfile.objects.filter(user__phone=self.candidate.phone).count(), 0)

    def test_vacancy_capacity_requires_admin_reasoned_override(self):
        existing_user = User.objects.create_user(
            phone="9777777799", password=None, role="ENGINEER", first_name="Existing", is_verified=False,
        )
        CompanyMembership.objects.create(company=self.company, user=existing_user, role="STAFF", is_active=True)
        existing_employee = EmployeeProfile.objects.create(
            company=self.company, user=existing_user, joining_date=timezone.localdate(),
            designation="ENGINEER", gender="OTHER",
        )
        existing_candidate = Candidate.objects.create(
            company=self.company, full_name="Existing Hire", phone="9777777798", created_by=self.office,
        )
        CandidateApplication.objects.create(
            company=self.company, candidate=existing_candidate, job_opening=self.job,
            stage="JOINED", converted_employee=existing_employee, created_by=self.office,
        )
        self._issue_and_accept_offer()
        self.client.force_authenticate(self.admin)
        blocked = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/convert/", {}, format="json")
        self.assertEqual(blocked.status_code, 409)
        missing_reason = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/convert/", {"capacity_override": True}, format="json")
        self.assertEqual(missing_reason.status_code, 409)
        overridden = self.client.post(f"/api/employees/hrms/recruitment/applications/{self.application.id}/convert/", {"capacity_override": True, "override_reason": "Approved emergency replacement hire"}, format="json")
        self.assertEqual(overridden.status_code, 201)
        self.assertTrue(RecruitmentAuditEvent.objects.filter(entity_type="JOB_OPENING", entity_id=self.job.id, action="VACANCY_OVERRIDE").exists())

    def test_summary_exposes_command_center_metrics_and_queues(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.summary)
        self.assertEqual(response.status_code, 200)
        self.assertIn("ats", response.data)
        self.assertIn("action_queue", response.data)
        self.assertIn("open_vacancies", response.data["jobs"])
