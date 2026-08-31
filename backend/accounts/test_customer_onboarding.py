from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from customers.models import Customer

from .models import PhoneOTP, User


@override_settings(DISABLE_AUTH_THROTTLING=True)
class CustomerOnboardingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _register_and_get_otp(self, phone, name="Customer"):
        response = self.client.post(
            "/api/auth/register/",
            {"first_name": name, "phone": phone, "password": "Strong@123"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/api/auth/send-otp/", {"phone": phone}, format="json")
        self.assertEqual(response.status_code, 200)
        return PhoneOTP.objects.get(user__phone=phone).otp

    def test_existing_customer_self_activates_and_is_linked_after_otp(self):
        customer = Customer.objects.create(
            name="Existing ARI Customer",
            phone="9200000001",
            address="Existing address",
            city="Bareilly",
            state="UP",
            pincode="243001",
            ro_model="ARI RO",
            monthly_rent="300.00",
        )
        otp = self._register_and_get_otp(customer.phone, customer.name)
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": customer.phone, "otp": otp},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["existing_customer_linked"])
        self.assertIn("access", response.data)
        customer.refresh_from_db()
        self.assertEqual(customer.user.phone, customer.phone)
        self.assertTrue(customer.user.is_verified)

    def test_new_shopper_can_create_verified_account_without_ro(self):
        phone = "9200000002"
        otp = self._register_and_get_otp(phone, "New Shopper")
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": phone, "otp": otp},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["existing_customer_linked"])
        self.assertFalse(Customer.objects.filter(phone=phone).exists())
        self.assertTrue(User.objects.get(phone=phone).is_verified)

    def test_unverified_customer_cannot_login(self):
        User.objects.create_user(
            phone="9200000003",
            password="Strong@123",
            role="CUSTOMER",
            is_verified=False,
        )
        response = self.client.post(
            "/api/auth/login/",
            {"phone": "9200000003", "password": "Strong@123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_unverified_account_can_securely_set_password_after_otp(self):
        user = User.objects.create_user(
            phone="9200000005",
            password="OldStrong@123",
            role="CUSTOMER",
            is_verified=False,
        )
        self.client.post("/api/auth/send-otp/", {"phone": user.phone}, format="json")
        otp = PhoneOTP.objects.get(user=user).otp
        response = self.client.post(
            "/api/auth/verify-otp/",
            {"phone": user.phone, "otp": otp, "new_password": "NewStrong@123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrong@123"))

    def test_five_wrong_passwords_temporarily_lock_account_and_are_audited(self):
        user = User.objects.create_user(
            phone="9200000004",
            password="Strong@123",
            role="CUSTOMER",
            is_verified=True,
        )
        for _ in range(5):
            response = self.client.post(
                "/api/auth/login/",
                {"phone": user.phone, "password": "Wrong@123"},
                format="json",
            )
            self.assertEqual(response.status_code, 401)
        user.refresh_from_db()
        self.assertIsNotNone(user.locked_until)
        response = self.client.post(
            "/api/auth/login/",
            {"phone": user.phone, "password": "Strong@123"},
            format="json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertTrue(user.security_events.filter(event_type="ACCOUNT_LOCKED").exists())
