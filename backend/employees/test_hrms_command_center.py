from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from attendance.models import Attendance
from tenancy.models import Company, CompanyMembership
from .models import EmployeeDocument, EmployeeProfile, LeaveRequest


class HrmsCommandCenterTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ARI SMART RO HRMS TEST",
            slug="ari-smart-ro-hrms-test",
            phone="9000000100",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9000000101",
            password="Strong@Test1",
            role="ADMIN",
            first_name="Admin",
            is_verified=True,
            is_active=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9000000102",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Engineer",
            is_verified=True,
            is_active=True,
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
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("25000"),
        )
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            status="PRESENT",
            working_hours=Decimal("8"),
        )
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type="FULL_DAY",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            reason="Test",
            status="PENDING",
        )
        self.document = EmployeeDocument.objects.create(
            employee=self.employee,
            document_type="PAN",
            document_number="ABCDE1234F",
            verified=False,
        )

    def test_admin_sees_enterprise_hrms_summary(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/employees/hrms/command-center/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["headcount"]["active"], 1)
        self.assertEqual(response.data["attendance_today"]["present"], 1)
        self.assertEqual(response.data["leave"]["pending"], 1)
        self.assertEqual(response.data["documents"]["total"], 1)
        self.assertEqual(len(response.data["employees"]), 1)

    def test_employee_cannot_see_company_command_center(self):
        self.client.force_authenticate(self.employee_user)
        response = self.client.get("/api/employees/hrms/command-center/")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_verify_employee_document(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f"/api/employees/hrms/documents/{self.document.id}/action/",
            {"action": "VERIFY"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.document.refresh_from_db()
        self.assertTrue(self.document.verified)

    def test_employee_can_only_list_own_documents(self):
        self.client.force_authenticate(self.employee_user)
        response = self.client.get("/api/employees/hrms/documents/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["documents"]), 1)
        self.assertEqual(
            response.data["documents"][0]["employee_code"],
            self.employee.employee_id,
        )
