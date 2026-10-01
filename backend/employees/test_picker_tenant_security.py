from datetime import date

from rest_framework.test import APITestCase

from accounts.models import User
from employees.models import EmployeeProfile
from tenancy.models import Company, CompanyMembership


class EmployeePickerTenantTests(APITestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Picker Tenant A",
            slug="picker-tenant-a",
            phone="9444400001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Picker Tenant B",
            slug="picker-tenant-b",
            phone="9444400002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9444400010",
            password="Strong@123",
            role="ADMIN",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        self.engineer_a_user = User.objects.create_user(
            phone="9444400011",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
        )
        self.engineer_b_user = User.objects.create_user(
            phone="9444400012",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=self.engineer_a_user,
            employee_id="PICK-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            is_active=True,
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=self.engineer_b_user,
            employee_id="PICK-B",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            is_active=True,
        )
        self.client.force_authenticate(self.admin)

    def test_engineer_list_is_tenant_scoped(self):
        response = self.client.get("/api/employees/engineers/")

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(self.engineer_a.id, ids)
        self.assertNotIn(self.engineer_b.id, ids)

    def test_assignment_employee_list_is_tenant_scoped(self):
        response = self.client.get("/api/employees/assignment-employees/")

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(self.engineer_a.id, ids)
        self.assertNotIn(self.engineer_b.id, ids)
