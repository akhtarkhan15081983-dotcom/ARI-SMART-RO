from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership, RoleFeaturePermission

from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .models import EmployeeDocument, EmployeeProfile


class CorporateHrPhase1GapTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Phase1 HR",
            slug="phase1-hr",
            phone="9444444400",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9444444401", password="Strong@Test1", role="ADMIN",
            first_name="HR", last_name="Admin", is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.admin, role="OWNER", is_active=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9444444402", password="Strong@Test1", role="ENGINEER",
            first_name="Field", last_name="Engineer", is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-P1-1",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("22000"),
            job_title="Service Engineer",
            department="Service",
            emergency_contact="9444444499",
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.employee_user, role="STAFF", is_active=True,
        )
        self.client.force_authenticate(self.admin)
        self.documents_url = f"/api/employees/hrms/employees/{self.employee.id}/documents/"
        self.file_url = f"/api/employees/hrms/employees/{self.employee.id}/"
        self.action_url = f"/api/employees/hrms/employees/{self.employee.id}/action/"

    def _upload(self, kind, *, expiry=None):
        payload = {
            "document_type": kind,
            "document_number": f"{kind}-001",
            "file": SimpleUploadedFile(f"{kind.lower()}.pdf", b"phase1-document", content_type="application/pdf"),
        }
        if expiry:
            payload["expiry_date"] = expiry
        return self.client.post(self.documents_url, payload, format="multipart")

    def _verify(self, document_id, reason="Source document checked by HR."):
        return self.client.patch(
            self.documents_url,
            {"document_id": document_id, "action": "VERIFY", "reason": reason},
            format="json",
        )

    def _verified_required_documents(self):
        for kind in (
            "PHOTO", "AADHAAR", "PAN", "ADDRESS_PROOF", "BANK_PROOF",
            "QUALIFICATION", "PREVIOUS_EMPLOYMENT",
        ):
            uploaded = self._upload(kind)
            self.assertEqual(uploaded.status_code, 201)
            verified = self._verify(uploaded.data["id"])
            self.assertEqual(verified.status_code, 200)

    def _complete_non_document_controls(self):
        self.employee.photo = "employees/test/phase1-ready.jpg"
        self.employee.face_enrollment_verified = True
        self.employee.attendance_device_id = "PHASE1-DEVICE"
        self.employee.save(update_fields=["photo", "face_enrollment_verified", "attendance_device_id"])
        response = self.client.patch(
            self.file_url,
            {
                "policy_acknowledged": True,
                "sop_acknowledged": True,
                "safety_training_acknowledged": True,
                "payroll_details_complete": True,
                "joining_checklist": {"joining_form": True},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        for action in ("MANAGER_REVIEW", "HR_REVIEW"):
            reviewed = self.client.post(
                self.action_url,
                {"action": action, "status": "APPROVED", "note": f"{action} complete."},
                format="json",
            )
            self.assertEqual(reviewed.status_code, 200)

    def test_document_contract_lists_all_required_types_as_missing(self):
        response = self.client.get(self.documents_url)
        self.assertEqual(response.status_code, 200)
        statuses = {row["document_type"]: row["status"] for row in response.data["documents"]}
        for kind in ("PHOTO", "AADHAAR", "PAN", "ADDRESS_PROOF", "BANK_PROOF", "QUALIFICATION", "PREVIOUS_EMPLOYMENT"):
            self.assertEqual(statuses[kind], "MISSING")
        self.assertIn("OTHER", response.data["document_types"])

    def test_upload_verify_reject_expire_are_audited_with_reviewer_and_reason(self):
        uploaded = self._upload("AADHAAR")
        self.assertEqual(uploaded.status_code, 201)
        self.assertEqual(uploaded.data["status"], "UPLOADED")
        document_id = uploaded.data["id"]

        verified = self._verify(document_id, "Aadhaar original matched.")
        self.assertEqual(verified.data["status"], "VERIFIED")
        self.assertEqual(verified.data["reviewer"], "HR Admin")
        self.assertEqual(verified.data["reason"], "Aadhaar original matched.")

        rejected = self.client.patch(
            self.documents_url,
            {"document_id": document_id, "action": "REJECT", "reason": "Image unreadable."},
            format="json",
        )
        self.assertEqual(rejected.data["status"], "REJECTED")
        self.assertTrue(any(item["event"] == "DOCUMENT_REJECTED" for item in rejected.data["audit"]))

        expired = self.client.patch(
            self.documents_url,
            {"document_id": document_id, "action": "EXPIRE", "reason": "Renewal required."},
            format="json",
        )
        self.assertEqual(expired.data["status"], "EXPIRED")
        self.assertTrue(EmployeeHrLifecycleEvent.objects.filter(
            employee=self.employee, event_type="DOCUMENT_EXPIRED", created_by=self.admin,
        ).exists())

    def test_document_operations_are_tenant_isolated(self):
        other_company = Company.objects.create(
            name="Other Tenant", slug="other-phase1", phone="9555555500",
            is_active=True, lifecycle_status="ACTIVE",
        )
        other_user = User.objects.create_user(
            phone="9555555501", password="Strong@Test1", role="ENGINEER", is_verified=True,
        )
        other_employee = EmployeeProfile.objects.create(
            company=other_company, user=other_user, employee_id="EMP-OTHER-P1",
            joining_date=timezone.localdate(), designation="ENGINEER", gender="MALE",
            job_title="Engineer", department="Service", emergency_contact="9555555599",
        )
        foreign_url = f"/api/employees/hrms/employees/{other_employee.id}/documents/"
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        upload = self.client.post(
            foreign_url,
            {"document_type": "PAN", "file": SimpleUploadedFile("pan.pdf", b"x")},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 404)

    def test_rejected_and_expired_documents_block_ready(self):
        self._verified_required_documents()
        self._complete_non_document_controls()
        ready = self.client.get(self.file_url)
        self.assertTrue(ready.data["lifecycle"]["readiness"]["ready"])

        pan = EmployeeDocument.objects.get(employee=self.employee, document_type="PAN")
        rejected = self.client.patch(
            self.documents_url,
            {"document_id": pan.id, "action": "REJECT", "reason": "Mismatch."},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200)
        blocked = self.client.get(self.file_url)
        self.assertFalse(blocked.data["lifecycle"]["readiness"]["ready_without_override"])

        self._verify(pan.id, "Corrected PAN matched.")
        aadhaar = EmployeeDocument.objects.get(employee=self.employee, document_type="AADHAAR")
        self.client.patch(
            self.documents_url,
            {"document_id": aadhaar.id, "action": "EXPIRE", "reason": "Expired evidence."},
            format="json",
        )
        expired_blocked = self.client.get(self.file_url)
        self.assertFalse(expired_blocked.data["lifecycle"]["readiness"]["ready_without_override"])

    def test_expired_documents_are_in_command_center_action_queue(self):
        expired = self._upload(
            "BANK_PROOF", expiry=(timezone.localdate() - timedelta(days=2)).isoformat()
        )
        self.assertEqual(expired.status_code, 201)
        dashboard = self.client.get("/api/employees/hrms/corporate-dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        matches = [row for row in dashboard.data["action_queue"] if row["document_id"] == expired.data["id"]]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["action"], "EXPIRED_DOCUMENT")

    def test_ready_transition_persists_only_valid_status_for_every_employment_type(self):
        valid_statuses = {value for value, _ in EmployeeHrLifecycle.EMPLOYMENT_STATUSES}
        self._verified_required_documents()
        self._complete_non_document_controls()
        expected = {
            "PROBATION": "PROBATION",
            "PERMANENT": "CONFIRMED",
            "CONTRACT": "CONFIRMED",
            "TRAINEE": "PROBATION",
        }
        lifecycle = EmployeeHrLifecycle.objects.get(employee=self.employee)
        for employment_type, expected_status in expected.items():
            lifecycle.employment_type = employment_type
            lifecycle.employment_status = "ONBOARDING"
            lifecycle.hr_stage = "HR_REVIEW"
            lifecycle.save(update_fields=["employment_type", "employment_status", "hr_stage", "updated_at"])
            response = self.client.get(self.file_url)
            self.assertTrue(response.data["lifecycle"]["readiness"]["ready"])
            lifecycle.refresh_from_db()
            self.assertIn(lifecycle.employment_status, valid_statuses)
            self.assertEqual(lifecycle.employment_status, expected_status)

    def test_hr_segregation_of_duties(self):
        manager = User.objects.create_user(
            phone="9444444410", password="Strong@Test1", role="MANAGER", is_verified=True,
        )
        CompanyMembership.objects.create(company=self.company, user=manager, role="MANAGER", is_active=True)
        office = User.objects.create_user(
            phone="9444444411", password="Strong@Test1", role="OFFICE", is_verified=True,
        )
        CompanyMembership.objects.create(company=self.company, user=office, role="STAFF", is_active=True)

        self.client.force_authenticate(manager)
        self.assertEqual(self.client.post(
            self.action_url, {"action": "MANAGER_REVIEW", "status": "APPROVED", "note": "Manager review."}, format="json"
        ).status_code, 200)
        self.assertEqual(self.client.post(
            self.action_url, {"action": "HR_REVIEW", "status": "APPROVED", "note": "Not HR."}, format="json"
        ).status_code, 403)
        self.assertEqual(self.client.post(
            self.action_url, {"action": "START_NOTICE", "note": "Not HR."}, format="json"
        ).status_code, 403)

        self.client.force_authenticate(office)
        self.assertEqual(self.client.post(
            self.action_url, {"action": "HR_REVIEW", "status": "APPROVED", "note": "Unauthorized office."}, format="json"
        ).status_code, 403)
        RoleFeaturePermission.objects.create(
            company=self.company, role="OFFICE", feature_key="employee_management", is_allowed=True,
            updated_by=self.admin,
        )
        self.assertEqual(self.client.post(
            self.action_url, {"action": "HR_REVIEW", "status": "APPROVED", "note": "Authorized HR review."}, format="json"
        ).status_code, 200)
        self.assertEqual(self.client.post(
            self.action_url, {"action": "OVERRIDE_READY", "note": "Office cannot override."}, format="json"
        ).status_code, 403)

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(
            self.action_url, {"action": "OVERRIDE_READY"}, format="json"
        ).status_code, 400)
        override = self.client.post(
            self.action_url, {"action": "OVERRIDE_READY", "note": "Admin emergency override with accountability."}, format="json"
        )
        self.assertEqual(override.status_code, 200)
        self.assertTrue(EmployeeHrLifecycleEvent.objects.filter(
            employee=self.employee, event_type="OVERRIDE_READY", created_by=self.admin,
            note__contains="accountability",
        ).exists())
