from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from customers.models import Customer


@override_settings(
    DISABLE_AUTH_THROTTLING=True,
    EXISTING_CUSTOMER_TEMP_PASSWORD="ARI-Existing@2026",
)
class ExistingCustomerAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            name="Existing Customer",
            phone="9300000001",
            address="Address",
            city="Agra",
            state="UP",
            pincode="282001",
            ro_model="ARI RO",
        )

    def test_existing_customer_must_replace_temporary_password(self):
        start = self.client.post(
            "/api/auth/existing-customer/start/",
            {
                "identifier": self.customer.customer_id,
                "temporary_password": "ARI-Existing@2026",
            },
            format="json",
        )
        self.assertEqual(start.status_code, 200)
        token = start.data["activation_token"]

        same = self.client.post(
            "/api/auth/existing-customer/complete/",
            {"activation_token": token, "new_password": "ARI-Existing@2026"},
            format="json",
        )
        self.assertEqual(same.status_code, 400)

        complete = self.client.post(
            "/api/auth/existing-customer/complete/",
            {"activation_token": token, "new_password": "PersonalStrong@123"},
            format="json",
        )
        self.assertEqual(complete.status_code, 201)
        self.customer.refresh_from_db()
        self.assertIsNotNone(self.customer.user_id)
        self.assertTrue(self.customer.user.is_verified)

    def test_shared_mobile_requires_customer_or_card_reference(self):
        other = Customer.objects.create(
            name="Second Customer",
            phone=self.customer.phone,
            address="Address 2",
            city="Agra",
            state="UP",
            pincode="282001",
            ro_model="ARI RO",
        )
        by_phone = self.client.post(
            "/api/auth/existing-customer/start/",
            {
                "identifier": self.customer.phone,
                "temporary_password": "ARI-Existing@2026",
            },
            format="json",
        )
        self.assertEqual(by_phone.status_code, 404)
        self.assertEqual(by_phone.data["code"], "AMBIGUOUS_PHONE")

        by_card = self.client.post(
            "/api/auth/existing-customer/start/",
            {
                "identifier": other.card_number,
                "temporary_password": "ARI-Existing@2026",
            },
            format="json",
        )
        self.assertEqual(by_card.status_code, 200)
