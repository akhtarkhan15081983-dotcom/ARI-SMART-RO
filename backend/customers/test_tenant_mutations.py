from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer
from tenancy.models import Company, CompanyMembership


class CustomerTenantMutationTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Customer Tenant A",
            slug="customer-tenant-a",
            phone="9000800001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Customer Tenant B",
            slug="customer-tenant-b",
            phone="9000800002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin_a = User.objects.create_user(
            phone="9000800011",
            password="Strong@123",
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
        self.customer_a = self._customer(self.company_a, "9000800021", "Tenant A")
        self.customer_b = self._customer(self.company_b, "9000800022", "Tenant B")
        self.client = APIClient()
        self.client.force_authenticate(self.admin_a)

    def _customer(self, company, phone, name):
        return Customer.objects.create(
            company=company,
            name=name,
            phone=phone,
            address="Test address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
            monthly_rent=Decimal("900.00"),
        )

    def test_admin_cannot_edit_other_company_customer(self):
        response = self.client.patch(
            f"/api/customers/{self.customer_b.id}/update/",
            {"name": "Cross tenant edit"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.customer_b.refresh_from_db()
        self.assertEqual(self.customer_b.name, "Tenant B")

    def test_admin_cannot_change_other_company_customer_lifecycle(self):
        response = self.client.post(
            f"/api/customers/{self.customer_b.id}/lifecycle/",
            {"action": "deactivate", "reason": "Must not cross tenant"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.customer_b.refresh_from_db()
        self.assertTrue(self.customer_b.is_active)

    def test_admin_cannot_capture_location_for_other_company_customer(self):
        response = self.client.post(
            f"/api/customers/{self.customer_b.id}/capture-location/",
            {"latitude": "27.1766700", "longitude": "78.0080700"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.customer_b.refresh_from_db()
        self.assertIsNone(self.customer_b.latitude)
        self.assertIsNone(self.customer_b.longitude)

    def test_admin_can_edit_same_company_customer(self):
        response = self.client.patch(
            f"/api/customers/{self.customer_a.id}/update/",
            {"name": "Updated Tenant A"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.customer_a.refresh_from_db()
        self.assertEqual(self.customer_a.name, "Updated Tenant A")
