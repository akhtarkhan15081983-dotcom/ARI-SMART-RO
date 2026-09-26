from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer


class CustomerFullEditTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9500000001",
            password="AdminStrong@123",
            first_name="Admin",
            role="ADMIN",
            is_active=True,
            is_verified=True,
        )
        self.customer = Customer.objects.create(
            name="Old Name",
            phone="9500000002",
            address="Old Address",
            city="Mathura",
            state="UP",
            pincode="281001",
            ro_model="Old RO",
            monthly_rent=Decimal("900.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("2400.00"),
        )
        self.original_customer_id = self.customer.customer_id
        self.original_card_number = self.customer.card_number
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_edit_customer_business_fields_but_not_core_ids(self):
        response = self.client.patch(
            f"/api/customers/{self.customer.id}/update/",
            {
                "customer_id": "HACKED-CUSTOMER-ID",
                "card_number": "HACKED-CARD-NUMBER",
                "old_card_number": "OLD-7788",
                "name": "Updated Name",
                "phone": "9500000099",
                "alternate_phone": "9500000088",
                "email": "updated@example.com",
                "gender": "MALE",
                "address": "Updated Address",
                "area": "Krishna Nagar",
                "city": "Mathura",
                "state": "Uttar Pradesh",
                "pincode": "281004",
                "latitude": "27.4924134",
                "longitude": "77.6736730",
                "ro_model": "ARI Smart RO Pro",
                "installation_charge": "650.00",
                "monthly_rent": "950.00",
                "security_deposit": "2600.00",
                "ownership_type": "PURCHASE",
                "rent_to_purchase_amount": "15000.00",
                "rent_at_conversion": "950.00",
                "security_adjusted_at_conversion": "2600.00",
                "rent_to_purchase_notes": "Converted after customer approval",
                "installation_date": "2026-04-01",
                "is_active": False,
                "deactivation_reason": "Temporary hold",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()

        self.assertEqual(self.customer.customer_id, self.original_customer_id)
        self.assertEqual(self.customer.card_number, self.original_card_number)
        self.assertEqual(self.customer.old_card_number, "OLD-7788")
        self.assertEqual(self.customer.name, "Updated Name")
        self.assertEqual(self.customer.phone, "9500000099")
        self.assertEqual(self.customer.ro_model, "ARI Smart RO Pro")
        self.assertEqual(self.customer.monthly_rent, Decimal("950.00"))
        self.assertEqual(self.customer.security_deposit, Decimal("2600.00"))
        self.assertEqual(self.customer.ownership_type, "PURCHASE")
        self.assertFalse(self.customer.is_active)
        self.assertEqual(self.customer.deactivation_reason, "Temporary hold")

    def test_invalid_coordinates_are_rejected(self):
        response = self.client.patch(
            f"/api/customers/{self.customer.id}/update/",
            {"latitude": "91.0000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.latitude)
