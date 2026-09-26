from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.services.sms import memory_outbox
from customers.models import Customer


@override_settings(
    DISABLE_AUTH_THROTTLING=True,
    OTP_SMS_BACKEND="memory",
)
class ExistingCustomerAccessTests(TestCase):
    def setUp(self):
        memory_outbox.clear()
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

    def test_existing_customer_activation_requires_registered_mobile_otp(self):
        start = self.client.post(
            "/api/auth/existing-customer/start/",
            {"identifier": self.customer.customer_id},
            format="json",
            HTTP_X_ARI_DEVICE_ID="existing-customer-device",
        )
        self.assertEqual(start.status_code, 200)
        self.assertNotIn("phone", start.data["customer"])
        self.assertTrue(start.data["destination"].endswith("0001"))
        token = start.data["activation_token"]
        otp = memory_outbox[-1]["otp"]

        wrong = self.client.post(
            "/api/auth/existing-customer/complete/",
            {
                "activation_token": token,
                "otp": "000000" if otp != "000000" else "111111",
                "new_password": "PersonalStrong@123",
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="existing-customer-device",
        )
        self.assertEqual(wrong.status_code, 400)

        complete = self.client.post(
            "/api/auth/existing-customer/complete/",
            {
                "activation_token": token,
                "otp": otp,
                "new_password": "PersonalStrong@123",
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="existing-customer-device",
        )
        self.assertEqual(complete.status_code, 201)
        self.customer.refresh_from_db()
        self.assertIsNotNone(self.customer.user_id)
        self.assertTrue(self.customer.user.is_verified)

    def test_existing_customer_otp_is_bound_to_starting_device(self):
        start = self.client.post(
            "/api/auth/existing-customer/start/",
            {"identifier": self.customer.customer_id},
            format="json",
            HTTP_X_ARI_DEVICE_ID="device-a",
        )
        denied = self.client.post(
            "/api/auth/existing-customer/complete/",
            {
                "activation_token": start.data["activation_token"],
                "otp": memory_outbox[-1]["otp"],
                "new_password": "PersonalStrong@123",
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="device-b",
        )
        self.assertEqual(denied.status_code, 403)

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
            {"identifier": self.customer.phone},
            format="json",
        )
        self.assertEqual(by_phone.status_code, 404)
        self.assertEqual(by_phone.data["code"], "AMBIGUOUS_PHONE")

        by_card = self.client.post(
            "/api/auth/existing-customer/start/",
            {"identifier": other.card_number},
            format="json",
        )
        self.assertEqual(by_card.status_code, 200)
