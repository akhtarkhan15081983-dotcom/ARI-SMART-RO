from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership

from .hr_lifecycle_models import EmployeeHrLifecycle
from .hr_phase2_ats_models import HrLetter
from .hr_phase2_letters_bgv import _bgv_aware_readiness
from .hr_phase2_letters_bgv_models import (
    BackgroundVerificationCase,
    BackgroundVerificationCheck,
    BgvPolicy,
    HrLetterAcknowledgement,
    HrLetterTemplate,
    HrLetterWorkflow,
)
from .hr_phase2_recruitment_models import (
    Candidate,
    CandidateApplication,
    JobOpening,
    ManpowerRequisition,
)
from .models import EmployeeProfile


class CorporateHrPhase2LettersBgvTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Letters BGV Tenant",
            slug="letters-bgv-tenant",
            phone="9333333300",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.other_company = Company.objects.create(
            name="Other Letters Tenant",
            slug="other-letters-tenant",
            phone="9333333390",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9333333301", password="Strong@Test1", role="ADMIN",
            first_name="HR", last_name="Admin", is_verified=True,
        )
        self.office = User.objects.create_user(
            phone="9333333302", password="Strong@Test1", role="OFFICE",
            first_name="HR", last_name="Officer", is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9333333303", password="Strong@Test1", role="ENGINEER",
            first_name="Employee", last_name="One", is_verified=True,
        )
        self.foreign_admin = User.objects.create_user(
            phone="9333333391", password="Strong@Test1", role="ADMIN",
            first_name="Foreign", last_name="Admin", is_verified=True,
        )
        CompanyMembership.objects.create(company=self.company, user=self.admin, role="OWNER", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.office, role="STAFF", is_active=True)
        CompanyMembership.objects.create(company=self.company, user=self.employee_user, role="STAFF", is_active=True)
        CompanyMembership.objects.create(company=self.other_company, user=self.foreign_admin, role="OWNER", is_active=True)
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            job_title="Service Engineer",
            department="Service",
            salary="28000",
            gender="OTHER",
        )
        lifecycle = self.employee.hr_lifecycle
        lifecycle.work_location = "Mathura"
        lifecycle.save(update_fields=["work_location", "updated_at"])

        self.templates = "/api/employees/hrms/letters/templates/"
        self.workflows = "/api/employees/hrms/letters/workflows/"
        self.issued = "/api/employees/hrms/letters/issued/"
        self.bgv_cases = "/api/employees/hrms/bgv/cases/"
        self.bgv_policy = "/api/employees/hrms/bgv/policy/"

    def _create_template(self, letter_type="APPOINTMENT", name="Appointment Standard"):
        self.client.force_authenticate(self.office)
        response = self.client.post(self.templates, {
            "name": name,
            "letter_type": letter_type,
            "subject": "{{letter_type}} - {{employee_name}}",
            "body": "Employee {{employee_id}} / {{job_title}} / {{company_name}}",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return HrLetterTemplate.objects.get(pk=response.data["id"])

    def _issue_letter(self):
        template = self._create_template()
        self.client.force_authenticate(self.office)
        created = self.client.post(self.workflows, {
            "employee_id": self.employee.id,
            "template_id": template.id,
            "effective_date": timezone.localdate().isoformat(),
        }, format="json")
        self.assertEqual(created.status_code, 201)
        workflow_id = created.data["id"]
        submitted = self.client.post(
            f"{self.workflows}{workflow_id}/action/", {"action": "SUBMIT"}, format="json"
        )
        self.assertEqual(submitted.status_code, 200)
        self.client.force_authenticate(self.admin)
        approved = self.client.post(
            f"{self.workflows}{workflow_id}/action/",
            {"action": "APPROVE", "reason": "Approved by HR head"}, format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.client.force_authenticate(self.office)
        issued = self.client.post(
            f"{self.workflows}{workflow_id}/action/", {"action": "ISSUE"}, format="json"
        )
        self.assertEqual(issued.status_code, 200)
        return HrLetterWorkflow.objects.get(pk=workflow_id), HrLetter.objects.get(pk=issued.data["issued_letter_id"])

    def _recruitment_application(self):
        req = ManpowerRequisition.objects.create(
            company=self.company, department="Service", job_title="Engineer",
            designation="ENGINEER", positions=1, employment_type="PROBATION",
            location="Mathura", justification="BGV test", status="APPROVED",
            requested_by=self.office, approved_by=self.admin, approved_at=timezone.now(),
        )
        job = JobOpening.objects.create(
            company=self.company, requisition=req, title="Engineer", vacancies=1,
            status="OPEN", opened_at=timezone.now(), created_by=self.office,
        )
        candidate = Candidate.objects.create(
            company=self.company, full_name="Candidate BGV", phone="9888888801",
            email="candidate@example.com", created_by=self.office,
        )
        application = CandidateApplication.objects.create(
            company=self.company, candidate=candidate, job_opening=job,
            stage="SCREENING", created_by=self.office,
        )
        return candidate, application

    def test_template_versioning_and_company_isolation(self):
        first = self._create_template()
        second = self._create_template()
        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)

        foreign_user = User.objects.create_user(
            phone="9333333392", password="Strong@Test1", role="ENGINEER",
            first_name="Other", is_verified=True,
        )
        CompanyMembership.objects.create(company=self.other_company, user=foreign_user, role="STAFF", is_active=True)
        foreign_employee = EmployeeProfile.objects.create(
            company=self.other_company, user=foreign_user,
            joining_date=timezone.localdate(), designation="ENGINEER", gender="OTHER",
        )
        self.client.force_authenticate(self.office)
        blocked = self.client.post(self.workflows, {
            "employee_id": foreign_employee.id,
            "template_id": first.id,
            "effective_date": timezone.localdate().isoformat(),
        }, format="json")
        self.assertEqual(blocked.status_code, 404)

    def test_approval_segregation_snapshot_hash_immutability_and_issue_retry(self):
        template = self._create_template()
        self.client.force_authenticate(self.office)
        created = self.client.post(self.workflows, {
            "employee_id": self.employee.id,
            "template_id": template.id,
            "effective_date": timezone.localdate().isoformat(),
        }, format="json")
        self.assertEqual(created.status_code, 201)
        workflow_id = created.data["id"]
        self.assertEqual(self.client.post(f"{self.workflows}{workflow_id}/action/", {"action": "SUBMIT"}, format="json").status_code, 200)
        denied = self.client.post(f"{self.workflows}{workflow_id}/action/", {"action": "APPROVE"}, format="json")
        self.assertEqual(denied.status_code, 403)

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f"{self.workflows}{workflow_id}/action/", {"action": "APPROVE", "reason": "Approved"}, format="json").status_code, 200)
        self.client.force_authenticate(self.office)
        issued = self.client.post(f"{self.workflows}{workflow_id}/action/", {"action": "ISSUE"}, format="json")
        self.assertEqual(issued.status_code, 200)
        letter = HrLetter.objects.get(pk=issued.data["issued_letter_id"])
        original_snapshot = dict(letter.snapshot)
        original_hash = letter.content_hash
        retry = self.client.post(f"{self.workflows}{workflow_id}/action/", {"action": "ISSUE"}, format="json")
        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.data["idempotent"])
        self.assertEqual(HrLetter.objects.filter(employee=self.employee, letter_type="APPOINTMENT").count(), 1)

        self.employee.job_title = "Changed Later"
        self.employee.salary = 99999
        self.employee.save(update_fields=["job_title", "salary"])
        template.subject_template = "Changed template"
        template.save(update_fields=["subject_template", "updated_at"])
        letter.refresh_from_db()
        self.assertEqual(letter.snapshot, original_snapshot)
        self.assertEqual(letter.content_hash, original_hash)

    def test_acknowledgement_is_final_and_does_not_change_snapshot(self):
        _, letter = self._issue_letter()
        original_snapshot = dict(letter.snapshot)
        original_hash = letter.content_hash
        self.client.force_authenticate(self.employee_user)
        response = self.client.post(
            f"{self.issued}{letter.id}/acknowledge/",
            {"status": "ACKNOWLEDGED", "note": "Received"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        duplicate = self.client.post(
            f"{self.issued}{letter.id}/acknowledge/",
            {"status": "DECLINED", "note": "Changed mind"}, format="json",
        )
        self.assertEqual(duplicate.status_code, 409)
        letter.refresh_from_db()
        self.assertEqual(letter.snapshot, original_snapshot)
        self.assertEqual(letter.content_hash, original_hash)
        self.assertEqual(HrLetterAcknowledgement.objects.filter(letter=letter).count(), 1)

    def test_bgv_identity_masks_sensitive_raw_values_and_final_decision_is_authorized(self):
        _, application = self._recruitment_application()
        self.client.force_authenticate(self.office)
        created = self.client.post(self.bgv_cases, {"application_id": application.id}, format="json")
        self.assertEqual(created.status_code, 201)
        case_id = created.data["id"]
        check = self.client.post(f"{self.bgv_cases}{case_id}/checks/", {
            "check_type": "IDENTITY",
            "status": "VERIFIED",
            "details": {
                "aadhaar_number": "123412341234",
                "pan_number": "ABCDE1234F",
                "name_match": True,
                "dob_match": True,
            },
            "evidence_reference": "ID-REF-1",
        }, format="json")
        self.assertEqual(check.status_code, 201)
        self.assertNotIn("aadhaar_number", check.data["details"])
        self.assertNotIn("pan_number", check.data["details"])
        self.assertTrue(check.data["details"]["name_match"])
        stored = BackgroundVerificationCheck.objects.get(pk=check.data["id"])
        self.assertNotIn("aadhaar_number", stored.details)
        denied = self.client.post(
            f"{self.bgv_cases}{case_id}/decision/",
            {"decision": "CLEAR", "reason": "Checks reviewed"}, format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.admin)
        decided = self.client.post(
            f"{self.bgv_cases}{case_id}/decision/",
            {"decision": "CLEAR", "reason": "Authorized HR decision"}, format="json",
        )
        self.assertEqual(decided.status_code, 200)
        self.assertEqual(decided.data["overall_status"], "CLEAR")

    def test_bgv_waiver_requires_admin_reason(self):
        _, application = self._recruitment_application()
        self.client.force_authenticate(self.office)
        case = self.client.post(self.bgv_cases, {"application_id": application.id}, format="json")
        self.assertEqual(case.status_code, 201)
        self.client.force_authenticate(self.admin)
        missing = self.client.post(
            f"{self.bgv_cases}{case.data['id']}/decision/", {"decision": "WAIVED"}, format="json"
        )
        self.assertEqual(missing.status_code, 400)
        waived = self.client.post(
            f"{self.bgv_cases}{case.data['id']}/decision/",
            {"decision": "WAIVED", "reason": "Executive approved legacy verification waiver"}, format="json",
        )
        self.assertEqual(waived.status_code, 200)
        self.assertEqual(waived.data["overall_status"], "WAIVED")

    def test_bgv_case_is_preserved_when_candidate_becomes_employee(self):
        candidate, application = self._recruitment_application()
        self.client.force_authenticate(self.office)
        created = self.client.post(self.bgv_cases, {"application_id": application.id}, format="json")
        self.assertEqual(created.status_code, 201)
        case = BackgroundVerificationCase.objects.get(pk=created.data["id"])
        self.assertIsNone(case.employee_id)

        converted_user = User.objects.create_user(
            phone=candidate.phone, password=None, role="ENGINEER",
            first_name="Candidate", is_verified=False,
        )
        CompanyMembership.objects.create(company=self.company, user=converted_user, role="STAFF", is_active=True)
        converted = EmployeeProfile.objects.create(
            company=self.company, user=converted_user, joining_date=timezone.localdate(),
            designation="ENGINEER", gender="OTHER",
        )
        application.converted_employee = converted
        application.stage = "JOINED"
        application.save(update_fields=["converted_employee", "stage", "updated_at"])
        case.refresh_from_db()
        self.assertEqual(case.employee_id, converted.id)
        self.assertEqual(BackgroundVerificationCase.objects.filter(application=application).count(), 1)

    def test_bgv_policy_defaults_optional_and_mandatory_gate_blocks_ready_without_case(self):
        self.client.force_authenticate(self.admin)
        default_policy = self.client.get(self.bgv_policy)
        self.assertEqual(default_policy.status_code, 200)
        self.assertFalse(default_policy.data["mandatory_before_ready"])
        updated = self.client.patch(
            self.bgv_policy,
            {"mandatory_before_ready": True, "required_checks": ["IDENTITY"]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertTrue(BgvPolicy.objects.get(company=self.company).mandatory_before_ready)

        lifecycle = EmployeeHrLifecycle.objects.get(employee=self.employee)
        lifecycle.employment_status = "ONBOARDING"
        lifecycle.hr_stage = "CREATED"
        lifecycle.save(update_fields=["employment_status", "hr_stage", "updated_at"])
        base_result = {
            "ready": True,
            "ready_without_override": True,
            "stage": "READY",
            "checks": {},
        }
        with patch("employees.hr_phase2_letters_bgv._base_readiness", return_value=base_result):
            result = _bgv_aware_readiness(self.employee, lifecycle)
        self.assertFalse(result["ready"])
        self.assertEqual(result["stage"], "HR_REVIEW")
        self.assertFalse(result["checks"]["bgv"])
        lifecycle.refresh_from_db()
        self.assertEqual(lifecycle.employment_status, "ONBOARDING")

    def test_digital_hr_file_contains_letters_and_bgv(self):
        _, letter = self._issue_letter()
        self.client.force_authenticate(self.office)
        bgv = self.client.post(self.bgv_cases, {"employee_id": self.employee.id}, format="json")
        self.assertEqual(bgv.status_code, 201)
        response = self.client.get(f"/api/employees/hrms/employees/{self.employee.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(row["id"] == letter.id for row in response.data["hr_letters"]))
        self.assertEqual(response.data["background_verification"]["id"], bgv.data["id"])
