from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer


class CustomerSelfServiceCompatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="0000004321",
            password="StrongTest@123",
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            user=self.user,
            name="Existing Customer",
            phone="9876543210",
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Legacy RO",
            monthly_rent=300,
        )
        Customer.objects.create(
            name="Other Customer",
            phone="9123456789",
            address="Other Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282002",
            ro_model="Other RO",
            monthly_rent=500,
        )
        self.client.force_authenticate(user=self.user)

    def test_customer_list_uses_linked_customer_not_login_phone(self):
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.customer.id)
        self.assertEqual(response.data[0]["phone"], "9876543210")

    def test_customer_rent_uses_linked_customer_not_login_phone(self):
        response = self.client.get("/api/customers/rent/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["customer"]["id"], self.customer.id)
        self.assertEqual(response.data["customer"]["phone"], "9876543210")
        self.assertEqual(response.data["ro"]["monthly_rent"], 300.0)

    def test_employee_profile_compat_returns_customer_profile(self):
        response = self.client.get("/api/employees/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "CUSTOMER")
        self.assertEqual(response.data["employee_id"], self.customer.customer_id)
        self.assertEqual(response.data["phone"], "9876543210")
