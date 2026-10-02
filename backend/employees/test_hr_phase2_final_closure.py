from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership, CompanySubscription, SubscriptionPlan

from .hr_lifecycle_models import EmployeeHrLifecycleEvent
from .models import EmployeeDocument, EmployeeProfile


class CorporateHrPhase2FinalClosureTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.company = Company.objects.create(
            name="Final Closure Tenant",
            slug="final-closure-tenant",
            phone="9444400000",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9444400001",
            password="Strong@Test1",
            role="ADMIN",
            first_name="Admin",
            is_verified=True,
        )
        self.office = User.objects.create_user(
            phone="9444400002",
            password="Strong@Test1",
            role="OFFICE",
            first_name="HR",
            is_verified=True,
        )
        self.manager_user = User.objects.create_user(
            phone="9444400003",
            password="Strong@Test1",
            role="MANAGER",
            first_name="Manager",
            is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9444400004",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Employee",
            is_verified=True,
        )
        for user, role in (
            (self.admin, "OWNER"),
            (self.office, "STAFF"),
            (self.manager_user, "STAFF"),
            (self.employee_user, "STAFF"),
        ):
            CompanyMembership.objects.create(
                company=self.company,
                user=user,
                role=role,
                is_active=True,
            )

        self.manager = EmployeeProfile.objects.create(
            company=self.company,
            user=self.manager_user,
            employee_id="MGR-CLOSE-1",
            joining_date=self.today,
            designation="MANAGER",
            job_title="Operations Manager",
            department="Operations",
            salary=Decimal("45000"),
            gender="OTHER",
            emergency_contact="9444400098",
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-CLOSE-1",
            joining_date=self.today,
            designation="ENGINEER",
            job_title="Service Engineer",
            department="Service",
            salary=Decimal("28000"),
            gender="OTHER",
            emergency_contact="9444400099",
            reporting_manager=self.manager,
            id_card_issued_at=None,
            id_card_valid_until=None,
        )
        lifecycle = self.employee.hr_lifecycle
        lifecycle.employment_type = "PROBATION"
        lifecycle.employment_status = "PROBATION"
        lifecycle.confirmation_due_date = self.today + timedelta(days=30)
        lifecycle.save()

        self.legacy_url = f"/api/employees/hrms/employees/{self.employee.id}/action/"
        self.phase2_actions = "/api/employees/hrms/lifecycle/actions/"

    def _auth(self, user):
        self.client.force_authenticate(user)

    def _make_fully_ready(self):
        self.employee.photo = SimpleUploadedFile(
            "employee.jpg", b"employee-photo", content_type="image/jpeg"
        )
        self.employee.face_enrollment_verified = True
        self.employee.attendance_device_id = "DEVICE-CLOSURE-1"
        self.employee.save(
            update_fields=["photo", "face_enrollment_verified", "attendance_device_id"]
        )

        document_types = (
            "PHOTO",
            "AADHAAR",
            "PAN",
            "ADDRESS_PROOF",
            "BANK_PROOF",
            "QUALIFICATION",
            "PREVIOUS_EMPLOYMENT",
        )
        first_document = None
        for document_type in document_types:
            row = EmployeeDocument.objects.create(
                employee=self.employee,
                document_type=document_type,
                document_number=f"DOC-{document_type}",
                file=SimpleUploadedFile(
                    f"{document_type.lower()}.txt",
                    b"verified-document",
                    content_type="text/plain",
                ),
                verified=True,
            )
            first_document = first_document or row

        EmployeeHrLifecycleEvent.objects.create(
            employee=self.employee,
            event_type="DOCUMENT_UPLOADED",
            from_status="",
            to_status="UPLOADED",
            note="Corporate joining document workflow started.",
            metadata={
                "document_id": first_document.id,
                "document_type": first_document.document_type,
                "document_status": "UPLOADED",
            },
            created_by=self.admin,
        )

        lifecycle = self.employee.hr_lifecycle
        lifecycle.policy_acknowledged = True
        lifecycle.sop_acknowledged = True
        lifecycle.safety_training_acknowledged = True
        lifecycle.payroll_details_complete = True
        lifecycle.manager_review_status = "APPROVED"
        lifecycle.hr_review_status = "APPROVED"
        lifecycle.hr_override_ready = False
        lifecycle.save()

    def test_sensitive_legacy_actions_are_blocked_without_state_change(self):
        self._auth(self.admin)
        for action in (
            "EXTEND_PROBATION",
            "CONFIRM",
            "START_NOTICE",
            "SEPARATE",
        ):
            with self.subTest(action=action):
                response = self.client.post(
                    self.legacy_url,
                    {"action": action, "note": "Legacy bypass attempt"},
                    format="json",
                )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.data["code"], "PHASE2_LIFECYCLE_REQUIRED")
                self.assertEqual(response.data["action"], action)

        self.employee.refresh_from_db()
        self.employee.user.refresh_from_db()
        lifecycle = self.employee.hr_lifecycle
        lifecycle.refresh_from_db()
        self.assertTrue(self.employee.is_active)
        self.assertTrue(self.employee.user.is_active)
        self.assertEqual(lifecycle.employment_type, "PROBATION")
        self.assertEqual(lifecycle.employment_status, "PROBATION")

    def test_phase1_onboarding_reviews_remain_available(self):
        self._auth(self.admin)
        manager = self.client.post(
            self.legacy_url,
            {
                "action": "MANAGER_REVIEW",
                "status": "APPROVED",
                "note": "Manager onboarding approval",
            },
            format="json",
        )
        self.assertEqual(manager.status_code, 200)

        hr = self.client.post(
            self.legacy_url,
            {
                "action": "HR_REVIEW",
                "status": "APPROVED",
                "note": "HR onboarding approval",
            },
            format="json",
        )
        self.assertEqual(hr.status_code, 200)
        self.employee.hr_lifecycle.refresh_from_db()
        self.assertEqual(self.employee.hr_lifecycle.manager_review_status, "APPROVED")
        self.assertEqual(self.employee.hr_lifecycle.hr_review_status, "APPROVED")

    def test_phase2_lifecycle_action_endpoint_remains_available(self):
        self._auth(self.office)
        response = self.client.post(
            self.phase2_actions,
            {
                "employee_id": self.employee.id,
                "action_type": "CONFIRMATION",
                "effective_date": str(self.today),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["action_type"], "CONFIRMATION")
        self.assertEqual(response.data["status"], "DRAFT")

    def test_unready_employee_has_reserved_identity_but_no_active_card(self):
        self._auth(self.employee_user)
        response = self.client.get("/api/employees/id-card/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["employee_id"], self.employee.employee_id)
        self.assertTrue(response.data["verification_code"])
        self.assertFalse(response.data["issued"])
        self.assertEqual(response.data["status"], "NOT_ISSUED")
        self.assertFalse(response.data["active"])
        self.assertFalse(response.data["readiness_qualified"])

        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.id_card_issued_at)
        self.assertIsNone(self.employee.id_card_valid_until)

        verify = self.client.get(
            f"/api/employees/verify-id/{self.employee.public_verification_code}/"
        )
        self.assertEqual(verify.status_code, 200)
        self.assertFalse(verify.data["verified"])
        self.assertEqual(verify.data["employee"]["status"], "NOT_ISSUED")

    def test_admin_ready_override_does_not_bypass_card_issuance_contract(self):
        lifecycle = self.employee.hr_lifecycle
        lifecycle.hr_override_ready = True
        lifecycle.hr_override_reason = "Emergency operational override"
        lifecycle.save(update_fields=["hr_override_ready", "hr_override_reason"])

        self._auth(self.employee_user)
        response = self.client.get("/api/employees/id-card/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["issued"])
        self.assertFalse(response.data["readiness_qualified"])
        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.id_card_issued_at)

    def test_full_readiness_issues_card_once_and_enables_qr_verification(self):
        self._make_fully_ready()
        self._auth(self.employee_user)

        first = self.client.get("/api/employees/id-card/")
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data["issued"])
        self.assertEqual(first.data["status"], "ISSUED")
        self.assertTrue(first.data["active"])
        self.assertTrue(first.data["readiness_qualified"])
        issued_at = first.data["issued_at"]
        self.assertIsNotNone(issued_at)

        second = self.client.get("/api/employees/id-card/")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["issued_at"], issued_at)

        verify = self.client.get(
            f"/api/employees/verify-id/{self.employee.public_verification_code}/"
        )
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.data["verified"])
        self.assertEqual(verify.data["employee"]["status"], "ISSUED")

    def test_new_employee_creation_reserves_id_without_issuing_card(self):
        plan = SubscriptionPlan.objects.get(code="starter")
        CompanySubscription.objects.create(
            company=self.company,
            plan=plan,
            status="ACTIVE",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self._auth(self.admin)
        response = self.client.post(
            "/api/employees/manage/",
            {
                "first_name": "New",
                "last_name": "Joiner",
                "phone": "9444400010",
                "email": "new.joiner@example.com",
                "designation": "ENGINEER",
                "gender": "OTHER",
                "joining_date": str(self.today),
                "initial_password": "Strong@Test2",
                "job_title": "Junior Service Engineer",
                "department": "Service",
                "emergency_name": "Emergency",
                "emergency_contact": "9444400011",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = EmployeeProfile.objects.get(id=response.data["employee"]["id"])
        self.assertTrue(created.employee_id)
        self.assertTrue(created.public_verification_code)
        self.assertIsNone(created.id_card_issued_at)
        self.assertIsNone(created.id_card_valid_until)
