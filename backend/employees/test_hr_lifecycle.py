from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership

from .hr_lifecycle_models import EmployeeHrLifecycle, EmployeeHrLifecycleEvent
from .models import EmployeeProfile


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
        CompanyMembership.objects.create(
            company=self.company,
            user=self.employee_user,
            role="STAFF",
            is_active=True,
        )
        self.client.force_authenticate(self.admin)

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

    def test_directory_and_digital_file_expose_professional_lifecycle(self):
        directory = self.client.get("/api/employees/hrms/directory/")
        self.assertEqual(directory.status_code, 200)
        self.assertEqual(len(directory.data["employees"]), 1)
        self.assertIn("lifecycle", directory.data["employees"][0])

        detail = self.client.get(f"/api/employees/hrms/employees/{self.employee.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["employee"]["employee_id"], "EMP-HR-0001")
        self.assertIn("readiness", detail.data["lifecycle"])
        self.assertFalse(detail.data["lifecycle"]["readiness"]["ready"])

    def test_profile_and_lifecycle_updates_are_audited(self):
        profile = self.client.patch(
            f"/api/employees/hrms/employees/{self.employee.id}/profile/",
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
            f"/api/employees/hrms/employees/{self.employee.id}/",
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
        self.assertGreaterEqual(
            EmployeeHrLifecycleEvent.objects.filter(employee=self.employee).count(),
            2,
        )

    def test_confirmation_requires_manager_and_hr_reviews(self):
        blocked = self.client.post(
            f"/api/employees/hrms/employees/{self.employee.id}/action/",
            {"action": "CONFIRM"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

        manager_review = self.client.post(
            f"/api/employees/hrms/employees/{self.employee.id}/action/",
            {"action": "MANAGER_REVIEW", "status": "APPROVED", "note": "Work quality verified."},
            format="json",
        )
        self.assertEqual(manager_review.status_code, 200)
        hr_review = self.client.post(
            f"/api/employees/hrms/employees/{self.employee.id}/action/",
            {"action": "HR_REVIEW", "status": "APPROVED", "note": "HR records reviewed."},
            format="json",
        )
        self.assertEqual(hr_review.status_code, 200)
        confirmed = self.client.post(
            f"/api/employees/hrms/employees/{self.employee.id}/action/",
            {"action": "CONFIRM", "note": "Probation completed."},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200)
        lifecycle = EmployeeHrLifecycle.objects.get(employee=self.employee)
        self.assertEqual(lifecycle.employment_status, "CONFIRMED")
        self.assertEqual(lifecycle.employment_type, "PERMANENT")
        self.assertIsNotNone(lifecycle.confirmed_at)

    def test_separation_preserves_employee_history_and_disables_login(self):
        notice = self.client.post(
            f"/api/employees/hrms/employees/{self.employee.id}/action/",
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
            f"/api/employees/hrms/employees/{self.employee.id}/action/",
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
