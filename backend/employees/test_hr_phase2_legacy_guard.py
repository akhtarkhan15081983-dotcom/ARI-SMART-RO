from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership
from .models import EmployeeProfile


class CorporateHrPhase2LegacyLifecycleGuardTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.company = Company.objects.create(
            name="Lifecycle Guard Tenant",
            slug="lifecycle-guard-tenant",
            phone="9333300000",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9333300001",
            password="Strong@Test1",
            role="ADMIN",
            first_name="Admin",
            is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9333300002",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Employee",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.employee_user,
            role="STAFF",
            is_active=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-GUARD-1",
            joining_date=self.today,
            designation="ENGINEER",
            job_title="Service Engineer",
            department="Service",
            salary=Decimal("28000"),
            gender="OTHER",
        )
        lifecycle = self.employee.hr_lifecycle
        lifecycle.employment_type = "PROBATION"
        lifecycle.employment_status = "PROBATION"
        lifecycle.save()
        self.url = f"/api/employees/hrms/employees/{self.employee.id}/action/"
        self.client.force_authenticate(self.admin)

    def test_phase2_sensitive_transitions_are_blocked_on_legacy_endpoint(self):
        for action in (
            "EXTEND_PROBATION",
            "CONFIRM",
            "START_NOTICE",
            "SEPARATE",
        ):
            with self.subTest(action=action):
                response = self.client.post(
                    self.url,
                    {"action": action, "note": "Legacy attempt"},
                    format="json",
                )
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.data["code"], "PHASE2_LIFECYCLE_REQUIRED")
                self.assertEqual(response.data["action"], action)

        self.employee.refresh_from_db()
        lifecycle = self.employee.hr_lifecycle
        lifecycle.refresh_from_db()
        self.assertTrue(self.employee.is_active)
        self.assertTrue(self.employee.user.is_active)
        self.assertEqual(lifecycle.employment_status, "PROBATION")
        self.assertEqual(lifecycle.employment_type, "PROBATION")

    def test_phase1_onboarding_review_action_remains_available(self):
        response = self.client.post(
            self.url,
            {
                "action": "MANAGER_REVIEW",
                "status": "APPROVED",
                "note": "Initial onboarding manager review",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.employee.hr_lifecycle.refresh_from_db()
        self.assertEqual(self.employee.hr_lifecycle.manager_review_status, "APPROVED")
