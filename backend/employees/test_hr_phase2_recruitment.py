from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership, RoleFeaturePermission

from .hr_phase2_recruitment_models import (
    Candidate,
    CandidateApplication,
    JobOpening,
    ManpowerRequisition,
    RecruitmentAuditEvent,
)


class CorporateHrPhase2RecruitmentTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Phase2 HR", slug="phase2-hr", phone="9555555500",
            is_active=True, lifecycle_status="ACTIVE",
        )
        self.other_company = Company.objects.create(
            name="Other Tenant", slug="phase2-other", phone="9555555590",
            is_active=True, lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9555555501", password="Strong@Test1", role="ADMIN",
            first_name="HR", last_name="Admin", is_verified=True,
        )
        self.office = User.objects.create_user(
            phone="9555555502", password="Strong@Test1", role="OFFICE",
            first_name="Recruitment", last_name="Officer", is_verified=True,
        )
        self.manager = User.objects.create_user(
            phone="9555555503", password="Strong@Test1", role="MANAGER",
            first_name="Hiring", last_name="Manager", is_verified=True,
        )
        self.other_admin = User.objects.create_user(
            phone="9555555591", password="Strong@Test1", role="ADMIN",
            first_name="Other", last_name="Admin", is_verified=True,
        )
        CompanyMembership.objects.create(company=self.company, user=self.admin, role="OWNER", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.office, role="STAFF", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.manager, role="MANAGER", is_active=True)
        CompanyMembership.objects.create(company=self.other_company, user=self.other_admin, role="OWNER", is_active=True)
        self.requisitions = "/api/employees/hrms/recruitment/requisitions/"
        self.jobs = "/api/employees/hrms/recruitment/jobs/"
        self.candidates = "/api/employees/hrms/recruitment/candidates/"
        self.applications = "/api/employees/hrms/recruitment/applications/"

    def _create_requisition(self, user=None):
        self.client.force_authenticate(user or self.office)
        response = self.client.post(self.requisitions, {
            "department": "Service",
            "job_title": "Service Engineer",
            "designation": "ENGINEER",
            "positions": 2,
            "employment_type": "PROBATION",
            "target_joining_date": (timezone.localdate() + timezone.timedelta(days=20)).isoformat(),
            "justification": "Approved workforce plan vacancy.",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def _approve_requisition(self, requisition_id):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"{self.requisitions}{requisition_id}/action/",
            {"action": "APPROVE"}, format="json",
        )
        self.assertEqual(response.status_code, 200)

    def _open_job(self, requisition_id):
        self.client.force_authenticate(self.office)
        response = self.client.post(self.jobs, {
            "requisition_id": requisition_id,
            "description": "Field service position",
            "requirements": "RO service experience preferred",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def test_requisition_requires_approval_segregation_and_audits_transition(self):
        requisition_id = self._create_requisition()
        self.client.force_authenticate(self.office)
        forbidden = self.client.post(
            f"{self.requisitions}{requisition_id}/action/", {"action": "APPROVE"}, format="json"
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.force_authenticate(self.manager)
        visible = self.client.get(self.requisitions)
        self.assertEqual(visible.status_code, 200)
        self.assertEqual(len(visible.data["requisitions"]), 1)

        self._approve_requisition(requisition_id)
        row = ManpowerRequisition.objects.get(pk=requisition_id)
        self.assertEqual(row.status, "APPROVED")
        self.assertEqual(row.approved_by_id, self.admin.id)
        self.assertTrue(RecruitmentAuditEvent.objects.filter(
            company=self.company, entity_type="MANPOWER_REQUISITION",
            entity_id=requisition_id, action="APPROVE", to_status="APPROVED",
        ).exists())

    def test_job_candidate_application_pipeline_enforces_valid_transitions(self):
        requisition_id = self._create_requisition()
        self._approve_requisition(requisition_id)
        job_id = self._open_job(requisition_id)

        self.client.force_authenticate(self.office)
        candidate_response = self.client.post(self.candidates, {
            "full_name": "Ravi Kumar", "phone": "9666666601",
            "email": "ravi@example.com", "experience_years": "3.5", "source": "Referral",
        }, format="json")
        self.assertEqual(candidate_response.status_code, 201)
        candidate_id = candidate_response.data["id"]

        application = self.client.post(self.applications, {
            "candidate_id": candidate_id, "job_id": job_id,
            "expected_salary": "28000", "notes": "Initial profile accepted",
        }, format="json")
        self.assertEqual(application.status_code, 201)
        application_id = application.data["id"]

        invalid = self.client.post(
            f"{self.applications}{application_id}/action/",
            {"stage": "SELECTED"}, format="json",
        )
        self.assertEqual(invalid.status_code, 400)

        for stage in ("SCREENING", "INTERVIEW", "SELECTED"):
            moved = self.client.post(
                f"{self.applications}{application_id}/action/", {"stage": stage}, format="json"
            )
            self.assertEqual(moved.status_code, 200)
            self.assertEqual(moved.data["stage"], stage)
        self.assertEqual(CandidateApplication.objects.get(pk=application_id).stage, "SELECTED")

    def test_recruitment_records_are_tenant_isolated(self):
        requisition_id = self._create_requisition()
        self._approve_requisition(requisition_id)
        self._open_job(requisition_id)

        self.client.force_authenticate(self.office)
        created = self.client.post(self.candidates, {
            "full_name": "Tenant Candidate", "phone": "9666666602",
        }, format="json")
        self.assertEqual(created.status_code, 201)

        self.client.force_authenticate(self.other_admin)
        self.assertEqual(self.client.get(self.requisitions).data["requisitions"], [])
        self.assertEqual(self.client.get(self.jobs).data["jobs"], [])
        self.assertEqual(self.client.get(self.candidates).data["candidates"], [])
        foreign_action = self.client.post(
            f"{self.requisitions}{requisition_id}/action/", {"action": "APPROVE"}, format="json"
        )
        self.assertEqual(foreign_action.status_code, 404)

    def test_candidate_phone_is_unique_per_company_not_globally(self):
        self.client.force_authenticate(self.office)
        first = self.client.post(self.candidates, {"full_name": "A", "phone": "9666666603"}, format="json")
        self.assertEqual(first.status_code, 201)
        duplicate = self.client.post(self.candidates, {"full_name": "B", "phone": "9666666603"}, format="json")
        self.assertEqual(duplicate.status_code, 409)

        self.client.force_authenticate(self.other_admin)
        other = self.client.post(self.candidates, {"full_name": "C", "phone": "9666666603"}, format="json")
        self.assertEqual(other.status_code, 201)
        self.assertEqual(Candidate.objects.filter(phone="9666666603").count(), 2)
