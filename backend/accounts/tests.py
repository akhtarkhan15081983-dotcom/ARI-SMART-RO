from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PhoneOTP


# ============================================================
# CUSTOMER REGISTRATION TESTS
# ============================================================

class CustomerRegistrationTests(TestCase):

    def setUp(self):

        self.client = APIClient()

    def test_customer_can_register(self):

        response = self.client.post(
            "/api/auth/register/",
            {
                "first_name": "Test",
                "last_name": "Customer",
                "phone": "9000000001",
                "password": "Test@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        user = User.objects.get(
            phone="9000000001"
        )

        self.assertEqual(
            user.role,
            "CUSTOMER",
        )

        self.assertFalse(
            user.is_verified
        )

        self.assertFalse(
            user.is_active
        )

    def test_registration_password_is_hashed(self):

        self.client.post(
            "/api/auth/register/",
            {
                "first_name": "Hash",
                "last_name": "Test",
                "phone": "9000000002",
                "password": "Test@123",
            },
            format="json",
        )

        user = User.objects.get(
            phone="9000000002"
        )

        self.assertNotEqual(
            user.password,
            "Test@123",
        )

        self.assertTrue(
            user.check_password(
                "Test@123"
            )
        )

    def test_duplicate_phone_is_rejected(self):

        User.objects.create_user(
            phone="9000000003",
            password="Existing@123",
            first_name="Existing",
            role="CUSTOMER",
        )

        response = self.client.post(
            "/api/auth/register/",
            {
                "first_name": "Another",
                "last_name": "Customer",
                "phone": "9000000003",
                "password": "Test@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_invalid_phone_is_rejected(self):

        response = self.client.post(
            "/api/auth/register/",
            {
                "first_name": "Invalid",
                "last_name": "Phone",
                "phone": "ABC1234567",
                "password": "Test@123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )


# ============================================================
# SEND OTP TESTS
# ============================================================

class SendOTPTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            phone="9000000010",
            password="Test@123",
            first_name="OTP",
            last_name="Test",
            role="CUSTOMER",
            is_verified=False,
        )

    def test_customer_can_request_otp(self):

        response = self.client.post(
            "/api/auth/send-otp/",
            {
                "phone": "9000000010",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.assertNotIn(
            "otp",
            response.data,
        )

        otp = PhoneOTP.objects.get(
            user=self.user
        )

        self.assertEqual(
            len(otp.otp),
            6,
        )

        self.assertTrue(
            otp.otp.isdigit()
        )

        self.assertFalse(
            otp.is_used
        )

    def test_otp_has_expiry(self):

        response = self.client.post(
            "/api/auth/send-otp/",
            {
                "phone": "9000000010",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        otp = PhoneOTP.objects.get(
            user=self.user
        )

        self.assertGreater(
            otp.expires_at,
            timezone.now(),
        )

    def test_non_existing_customer_cannot_request_otp(
        self
    ):

        response = self.client.post(
            "/api/auth/send-otp/",
            {
                "phone": "9000000099",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_verified_customer_cannot_request_otp(
        self
    ):

        self.user.is_verified = True

        self.user.save(
            update_fields=[
                "is_verified"
            ]
        )

        response = self.client.post(
            "/api/auth/send-otp/",
            {
                "phone": "9000000010",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    @override_settings(
        DEBUG=True,
        OTP_SMS_BACKEND="webhook",
        OTP_SMS_WEBHOOK_URL="https://example.invalid/otp",
        OTP_SMS_WEBHOOK_TOKEN="",
    )
    @patch("accounts.services.sms.urlopen", side_effect=OSError("gateway unavailable"))
    def test_delivery_failure_does_not_claim_otp_was_sent(self, mocked_urlopen):
        response = self.client.post(
            "/api/auth/send-otp/",
            {"phone": self.user.phone},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.data["success"])
        self.assertTrue(PhoneOTP.objects.get(user=self.user).is_used)
        mocked_urlopen.assert_called_once()


# ============================================================
# VERIFY OTP TESTS
# ============================================================

class VerifyOTPTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            phone="9000000020",
            password="Test@123",
            first_name="Verify",
            last_name="Test",
            role="CUSTOMER",
            is_verified=False,
        )

    def create_otp(
        self,
        otp="123456",
        expires_at=None,
    ):

        if expires_at is None:

            expires_at = (
                timezone.now()
                + timedelta(
                    minutes=5
                )
            )

        return PhoneOTP.objects.create(
            user=self.user,
            otp=otp,
            expires_at=expires_at,
        )

    def test_customer_can_verify_correct_otp(
        self
    ):

        otp = self.create_otp(
            otp="123456"
        )

        response = self.client.post(
            "/api/auth/verify-otp/",
            {
                "phone": "9000000020",
                "otp": "123456",
                "password": "Verified@12345",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.data["success"]
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.is_verified
        )

        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.check_password("Verified@12345"))
        self.assertFalse(self.user.check_password("Test@123"))

        otp.refresh_from_db()

        self.assertTrue(
            otp.is_used
        )

    def test_wrong_otp_is_rejected(self):

        otp = self.create_otp(
            otp="123456"
        )

        response = self.client.post(
            "/api/auth/verify-otp/",
            {
                "phone": "9000000020",
                "otp": "654321",
                "password": "Verified@12345",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

        otp.refresh_from_db()

        self.assertEqual(
            otp.attempts,
            1,
        )

    def test_expired_otp_is_rejected(self):

        otp = self.create_otp(
            otp="123456",
            expires_at=(
                timezone.now()
                - timedelta(
                    minutes=1
                )
            ),
        )

        response = self.client.post(
            "/api/auth/verify-otp/",
            {
                "phone": "9000000020",
                "otp": "123456",
                "password": "Verified@12345",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

        otp.refresh_from_db()

        self.assertTrue(
            otp.is_used
        )

    def test_used_otp_cannot_be_used_again(self):

        otp = self.create_otp(
            otp="123456"
        )

        otp.is_used = True

        otp.save(
            update_fields=[
                "is_used"
            ]
        )

        response = self.client.post(
            "/api/auth/verify-otp/",
            {
                "phone": "9000000020",
                "otp": "123456",
                "password": "Verified@12345",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

    def test_fifth_wrong_attempt_invalidates_otp(
        self
    ):

        otp = self.create_otp(
            otp="123456"
        )

        for index in range(5):

            response = self.client.post(
                "/api/auth/verify-otp/",
                {
                    "phone": "9000000020",
                    "otp": "999999",
                    "password": "Verified@12345",
                },
                format="json",
            )

            self.assertEqual(
                response.status_code,
                400,
            )

        otp.refresh_from_db()

        self.assertEqual(
            otp.attempts,
            5,
        )

        self.assertTrue(
            otp.is_used
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

    def test_invalid_otp_format_is_rejected(
        self
    ):

        self.create_otp(
            otp="123456"
        )

        response = self.client.post(
            "/api/auth/verify-otp/",
            {
                "phone": "9000000020",
                "otp": "12345",
                "password": "Verified@12345",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

    def test_new_otp_invalidates_previous_otp(
        self
    ):

        first_otp = self.create_otp(
            otp="123456"
        )

        response = self.client.post(
            "/api/auth/send-otp/",
            {
                "phone": "9000000020",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        first_otp.refresh_from_db()

        self.assertTrue(
            first_otp.is_used
        )

        active_otps = PhoneOTP.objects.filter(
            user=self.user,
            is_used=False,
        )

        self.assertEqual(
            active_otps.count(),
            1,
        )


class LoginSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unverified_customer_cannot_login(self):
        User.objects.create_user(
            phone="9000000030",
            password="Test@12345",
            role="CUSTOMER",
            is_verified=False,
            is_active=True,
        )

        response = self.client.post(
            "/api/auth/login/",
            {"phone": "9000000030", "password": "Test@12345"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("access", response.data)

    def test_verified_customer_can_login(self):
        User.objects.create_user(
            phone="9000000031",
            password="Test@12345",
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )

        response = self.client.post(
            "/api/auth/login/",
            {"phone": "9000000031", "password": "Test@12345"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_existing_token_for_unverified_customer_is_rejected(self):
        user = User.objects.create_user(
            phone="9000000032",
            password="Test@12345",
            role="CUSTOMER",
            is_verified=False,
            is_active=True,
        )
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get("/api/customers/")

        self.assertEqual(response.status_code, 401)
