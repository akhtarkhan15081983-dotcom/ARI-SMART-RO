from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer
from employees.models import EmployeeProfile
from tenancy.models import Company, CompanyMembership


class AssignedCustomersTenantTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Assigned Tenant A",
            slug="assigned-tenant-a",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Assigned Tenant B",
            slug="assigned-tenant-b",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.user = User.objects.create_user(
            phone="9222200001",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.user,
            role="STAFF",
            is_active=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            company=self.company_a,
            user=self.user,
            employee_id="ASSIGNED-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            is_active=True,
        )
        self.mine = Customer.objects.create(
            company=self.company_a,
            name="My Assigned Customer",
            phone="9222200002",
            address="Agra",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
            assigned_engineer=self.engineer,
        )
        self.other = Customer.objects.create(
            company=self.company_b,
            name="Wrong Tenant Customer",
            phone="9222200003",
            address="Delhi",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="ARI RO",
            assigned_engineer=self.engineer,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_my_customers_excludes_cross_tenant_assignment(self):
        response = self.client.get("/api/customers/my-customers/")

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(self.mine.id, ids)
        self.assertNotIn(self.other.id, ids)
