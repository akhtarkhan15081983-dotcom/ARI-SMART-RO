from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from employees.models import EmployeeProfile
from tenancy.models import Company, CompanyMembership

from .models import Attendance, AttendanceDeviceOverride


class AttendanceTenantSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company_a = Company.objects.create(
            name="Company A",
            slug="attendance-tenant-a",
            phone="9000000101",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Company B",
            slug="attendance-tenant-b",
            phone="9000000102",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin_a = User.objects.create_user(
            phone="9000000111",
            password="Strong@12345",
            first_name="Admin A",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.admin_a,
            role="ADMIN",
            is_active=True,
        )

        self.employee_a = self._employee(
            self.company_a, "9000000121", "EMP-TENANT-A"
        )
        self.employee_b = self._employee(
            self.company_b, "9000000122", "EMP-TENANT-B"
        )
        self.attendance_a = Attendance.objects.create(
            employee=self.employee_a,
            date=timezone.localdate(),
            check_in=timezone.now(),
            identity_review_status="PENDING",
        )
        self.attendance_b = Attendance.objects.create(
            employee=self.employee_b,
            date=timezone.localdate(),
            check_in=timezone.now(),
            identity_review_status="PENDING",
        )
        self.client.force_authenticate(user=self.admin_a)

    def _employee(self, company, phone, employee_id):
        user = User.objects.create_user(
            phone=phone,
            password="Strong@12345",
            first_name=employee_id,
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        return EmployeeProfile.objects.create(
            company=company,
            user=user,
            employee_id=employee_id,
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )

    def test_review_list_only_contains_current_company(self):
        response = self.client.get("/api/attendance/admin/reviews/?status=ALL")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(self.attendance_a.id, ids)
        self.assertNotIn(self.attendance_b.id, ids)

    def test_admin_cannot_review_other_company_attendance(self):
        response = self.client.post(
            f"/api/attendance/admin/reviews/{self.attendance_b.id}/",
            {"action": "approve", "note": "should not cross tenant"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.attendance_b.refresh_from_db()
        self.assertEqual(self.attendance_b.identity_review_status, "PENDING")

    def test_device_override_list_only_contains_current_company(self):
        response = self.client.get("/api/attendance/admin/device-overrides/")
        self.assertEqual(response.status_code, 200)
        employee_ids = {row["employee_id"] for row in response.data}
        self.assertIn("EMP-TENANT-A", employee_ids)
        self.assertNotIn("EMP-TENANT-B", employee_ids)

    def test_admin_cannot_grant_override_to_other_company_employee(self):
        response = self.client.post(
            f"/api/attendance/admin/device-overrides/{self.employee_b.id}/",
            {"action": "allow_today"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            AttendanceDeviceOverride.objects.filter(
                employee=self.employee_b,
                date=timezone.localdate(),
                is_active=True,
            ).exists()
        )
