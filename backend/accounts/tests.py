from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

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