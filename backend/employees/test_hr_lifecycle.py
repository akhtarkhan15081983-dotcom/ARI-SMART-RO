from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership

from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .models import EmployeeDocument, EmployeeProfile


class CorporateHrLifecycleTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Corporate HR Test",
            slug="corporate-hr-test",
            phone="9222222200",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9222222201",
            password="Strong@Test1",
            role="ADMIN",
            first_name="HR Admin",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9222222202",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Field",
            last_name="Engineer",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-HR-0001",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("22000"),
            job_title="Service Engineer",
            department="Service",
            grade="L1",
            emergency_contact="9222222299",
        )
        self.employee_membership = CompanyMembership.objects.create(
            company=self.company,
            user=self.employee_user,
            role="STAFF",
            is_active=True,
        )
        self.client.force_authenticate(self.admin)

    def _url(self, suffix=""):
        base = f"/api/employees/hrms/employees/{self.employee.id}/"
        return f"{base}{suffix}"

    def _add_verified_documents(self):
        for kind in ("AADHAAR", "PAN", "ADDRESS_PROOF", "BANK_PROOF", "PHOTO"):
            EmployeeDocument.objects.create(
                employee=self.employee,
                document_type=kind,
                verified=True,
            )

    def _complete_security(self):
        self.employee.photo = "employees/test/hr-ready.jpg"
        self.employee.face_enrollment_verified = True
        self.employee.attendance_device_id = "TEST-DEVICE-001"
        self.employee.save(
            update_fields=["photo", "face_enrollment_verified", "attendance_device_id"]
        )

    def _approve_reviews(self):
        for action, note in (
            ("MANAGER_REVIEW", "Manager verified probation performance."),
            ("HR_REVIEW", "HR verified employee file and controls."),
        ):
            response = self.client.post(
                self._url("action/"),
                {"action": action, "status": "APPROVED", "note": note},
                format="json",
            )
            self.assertEqual(response.status_code, 200)

    def _complete_lifecycle_controls(self):
        response = self.client.patch(
            self._url(),
            {
                "policy_acknowledged": True,
                "sop_acknowledged": True,
                "safety_training_acknowledged": True,
                "payroll_details_complete": True,
                "joining_checklist": {"joining_form": True},
                "note": "Mandatory onboarding controls completed.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_employee_profile_creates_lifecycle_record(self):
        lifecycle = EmployeeHrLifecycle.objects.get(employee=self.employee)
        self.assertEqual(lifecycle.employment_type, "PROBATION")
        self.assertEqual(lifecycle.employment_status, "ONBOARDING")
        self.assertIsNotNone(lifecycle.confirmation_due_date)

    def test_corporate_dashboard_returns_lifecycle_metrics(self):
        response = self.client.get("/api/employees/hrms/corporate-dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "CORPORATE_HR")
        self.assertEqual(response.data["workforce"]["active"], 1)
        self.assertGreaterEqual(response.data["workforce"]["pending_onboarding"], 1)
        self.assertIn("missing_required_documents", response.data["compliance"])
        self.assertIn("department_mix", response.data["workforce"])
        self.assertIn("designation_mix", response.data["workforce"])

    def test_dashboard_and_digital_file_are_tenant_isolated(self):
        other_company = Company.objects.create(
            name="Other Corporate HR",
            slug="other-corporate-hr",
            phone="9333333300",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        other_user = User.objects.create_user(
            phone="9333333301",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Other",
            is_verified=True,
        )
        other_employee = EmployeeProfile.objects.create(
            company=other_company,
            user=other_user,
            employee_id="EMP-OTHER-1",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            department="Other Service",
            job_title="Engineer",
            emergency_contact="9333333399",
        )
        CompanyMembership.objects.create(
            company=other_company,
            user=other_user,
            role="STAFF",
            is_active=True,
        )

        dashboard = self.client.get("/api/employees/hrms/corporate-dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["workforce"]["active"], 1)

        detail = self.client.get(
            f"/api/employees/hrms/employees/{other_employee.id}/"
        )
        self.assertEqual(detail.status_code, 404)

    def test_directory_and_digital_file_expose_professional_lifecycle(self):
        directory = self.client.get("/api/employees/hrms/directory/")
        self.assertEqual(directory.status_code, 200)
        self.assertEqual(len(directory.data["employees"]), 1)
        self.assertIn("lifecycle", directory.data["employees"][0])

        detail = self.client.get(self._url())
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["employee"]["employee_id"], "EMP-HR-0001")
        self.assertIn("readiness", detail.data["lifecycle"])
        self.assertFalse(detail.data["lifecycle"]["readiness"]["ready"])
        self.assertIn("manager_review", detail.data["lifecycle"]["readiness"]["checks"])
        self.assertIn("role_access", detail.data["lifecycle"]["readiness"])

    def test_profile_and_lifecycle_updates_are_audited(self):
        profile = self.client.patch(
            self._url("profile/"),
            {
                "date_of_birth": "1995-02-03",
                "aadhaar_number": "123456789012",
                "pan_number": "ABCDE1234F",
                "pincode": "282001",
                "job_title": "Senior Service Engineer",
            },
            format="json",
        )
        self.assertEqual(profile.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.date_of_birth, date(1995, 2, 3))
        self.assertEqual(self.employee.job_title, "Senior Service Engineer")

        lifecycle = self.client.patch(
            self._url(),
            {
                "employment_type": "PROBATION",
                "work_location": "Agra Branch",
                "probation_months": 6,
                "policy_acknowledged": True,
                "sop_acknowledged": True,
                "safety_training_acknowledged": True,
                "payroll_details_complete": True,
                "role_access_assigned": True,
                "joining_checklist": {"joining_form": True},
            },
            format="json",
        )
        self.assertEqual(lifecycle.status_code, 200)
        row = EmployeeHrLifecycle.objects.get(employee=self.employee)
        self.assertEqual(row.work_location, "Agra Branch")
        self.assertEqual(row.probation_months, 6)
        # Client cannot make role-access true by sending the old boolean flag;
        # the value is recalculated from membership + role permission matrix.
        self.assertTrue(row.role_access_assigned)
        self.assertGreaterEqual(
            EmployeeHrLifecycleEvent.objects.filter(employee=self.employee).count(),
            2,
        )

    def test_role_access_gate_uses_real_membership_not_client_boolean(self):
        self.employee_membership.is_active = False
        self.employee_membership.save(update_fields=["is_active"])
        response = self.client.patch(
            self._url(),
            {
                "role_access_assigned": True,
                "policy_acknowledged": True,
                "sop_acknowledged": True,
                "safety_training_acknowledged": True,
                "payroll_details_complete": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["readiness"]["checks"]["role_access"])
        row = EmployeeHrLifecycle.objects.get(employee=self.employee)
        self.assertFalse(row.role_access_assigned)

    def test_ready_requires_documents_security_manager_and_hr_review(self):
        self._complete_lifecycle_controls()
        early = self.client.get(self._url())
        self.assertFalse(early.data["lifecycle"]["readiness"]["ready"])
        self.assertFalse(early.data["lifecycle"]["readiness"]["checks"]["documents"])
        self.assertFalse(early.data["lifecycle"]["readiness"]["checks"]["security"])
        self.assertFalse(early.data["lifecycle"]["readiness"]["checks"]["manager_review"])

        self._add_verified_documents()
        self._complete_security()
        still_blocked = self.client.get(self._url())
        self.assertFalse(still_blocked.data["lifecycle"]["readiness"]["ready"])
        self.assertEqual(still_blocked.data["lifecycle"]["hr_stage"], "HR_REVIEW")

        self._approve_reviews()
        ready = self.client.get(self._url())
        self.assertTrue(ready.data["lifecycle"]["readiness"]["ready"])
        self.assertEqual(ready.data["lifecycle"]["hr_stage"], "READY")
        self.assertEqual(ready.data["lifecycle"]["employment_status"], "PROBATION")

    def test_admin_override_requires_reason_is_visible_and_audited(self):
        missing_reason = self.client.post(
            self._url("action/"),
            {"action": "OVERRIDE_READY"},
            format="json",
        )
        self.assertEqual(missing_reason.status_code, 400)

        override = self.client.post(
            self._url("action/"),
            {
                "action": "OVERRIDE_READY",
                "note": "Emergency supervised deployment approved by HR head.",
            },
            format="json",
        )
        self.assertEqual(override.status_code, 200)
        readiness = override.data["lifecycle"]["readiness"]
        self.assertTrue(readiness["override"])
        self.assertIn("Emergency supervised", readiness["override_reason"])
        event = EmployeeHrLifecycleEvent.objects.filter(
            employee=self.employee,
            event_type="OVERRIDE_READY",
        ).latest("created_at")
        self.assertTrue(event.metadata["override"])
        self.assertEqual(event.created_by, self.admin)

    def test_non_admin_cannot_override_ready(self):
        manager = User.objects.create_user(
            phone="9222222210",
            password="Strong@Test1",
            role="MANAGER",
            first_name="Manager",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=manager,
            role="MANAGER",
            is_active=True,
        )
        self.client.force_authenticate(manager)
        response = self.client.post(
            self._url("action/"),
            {"action": "OVERRIDE_READY", "note": "Attempted bypass."},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_probation_extension_requires_reason_and_is_audited(self):
        blocked = self.client.post(
            self._url("action/"),
            {"action": "EXTEND_PROBATION", "months": 2},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)

        before = EmployeeHrLifecycle.objects.get(employee=self.employee).confirmation_due_date
        extended = self.client.post(
            self._url("action/"),
            {
                "action": "EXTEND_PROBATION",
                "months": 2,
                "note": "Additional field quality assessment required.",
            },
            format="json",
        )
        self.assertEqual(extended.status_code, 200)
        row = EmployeeHrLifecycle.objects.get(employee=self.employee)
        self.assertGreater(row.confirmation_due_date, before)
        self.assertTrue(
            EmployeeHrLifecycleEvent.objects.filter(
                employee=self.employee,
                event_type="EXTEND_PROBATION",
            ).exists()
        )

    def test_confirmation_requires_manager_and_hr_reviews(self):
        blocked = self.client.post(
            self._url("action/"),
            {"action": "CONFIRM"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

        self._approve_reviews()
        confirmed = self.client.post(
            self._url("action/"),
            {"action": "CONFIRM", "note": "Probation completed."},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        lifecycle = EmployeeHrLifecycle.objects.get(employee=self.employee)
        self.assertEqual(lifecycle.employment_status, "CONFIRMED")
        self.assertEqual(lifecycle.employment_type, "PERMANENT")
        self.assertIsNotNone(lifecycle.confirmed_at)
        self.assertTrue(
            EmployeeHrLifecycleEvent.objects.filter(
                employee=self.employee,
                event_type="CONFIRM",
            ).exists()
        )

    def test_separation_preserves_employee_history_and_disables_login(self):
        notice = self.client.post(
            self._url("action/"),
            {
                "action": "START_NOTICE",
                "separation_type": "RESIGNATION",
                "last_working_date": timezone.localdate().isoformat(),
                "note": "Employee resignation accepted.",
            },
            format="json",
        )
        self.assertEqual(notice.status_code, 200)
        separated = self.client.post(
            self._url("action/"),
            {"action": "SEPARATE", "note": "Clearance complete."},
            format="json",
        )
        self.assertEqual(separated.status_code, 200)
        self.employee.refresh_from_db()
        self.employee_user.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertFalse(self.employee_user.is_active)
        self.assertTrue(EmployeeProfile.objects.filter(pk=self.employee.id).exists())
        self.assertTrue(EmployeeHrLifecycleEvent.objects.filter(employee=self.employee).exists())
