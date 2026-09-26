from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.services.sms import memory_outbox
from customers.models import Customer


@override_settings(
    DISABLE_AUTH_THROTTLING=True,
    OTP_SMS_BACKEND="memory",
)
class SecurityHardeningTests(TestCase):
    def setUp(self):
        memory_outbox.clear()

    def test_password_change_rejects_weak_password_and_revokes_old_refresh(self):
        user = User.objects.create_user(
            phone="9400000001",
            password="OldStrong@123",
            first_name="Engineer",
            role="ENGINEER",
            is_active=True,
        )
        old_refresh = RefreshToken.for_user(user)

        client = APIClient()
        client.force_authenticate(user=user)
        weak = client.post(
            "/api/auth/change-password/",
            {"old_password": "OldStrong@123", "new_password": "12345678"},
            format="json",
        )
        self.assertEqual(weak.status_code, 400)

        changed = client.post(
            "/api/auth/change-password/",
            {"old_password": "OldStrong@123", "new_password": "NewStrong@456"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertIn("access", changed.data)
        self.assertIn("refresh", changed.data)

        refresh_client = APIClient()
        old_session = refresh_client.post(
            "/api/auth/token/refresh/",
            {"refresh": str(old_refresh)},
            format="json",
        )
        self.assertEqual(old_session.status_code, 401)

    def test_admin_login_requires_mfa_before_tokens_are_issued(self):
        User.objects.create_user(
            phone="9400000002",
            password="AdminStrong@123",
            first_name="Admin",
            role="ADMIN",
            is_active=True,
            is_verified=True,
        )
        client = APIClient()
        login = client.post(
            "/api/auth/login/",
            {"phone": "9400000002", "password": "AdminStrong@123"},
            format="json",
            HTTP_X_ARI_DEVICE_ID="security-test-device",
        )
        self.assertEqual(login.status_code, 202)
        self.assertTrue(login.data["mfa_required"])
        self.assertNotIn("access", login.data)
        self.assertNotIn("refresh", login.data)
        self.assertEqual(memory_outbox[-1]["purpose"], "admin_login_mfa")

        verified = client.post(
            "/api/auth/admin/mfa/verify/",
            {
                "challenge": login.data["challenge"],
                "otp": memory_outbox[-1]["otp"],
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="security-test-device",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertIn("access", verified.data)
        self.assertIn("refresh", verified.data)

    def test_admin_mfa_is_bound_to_same_device(self):
        User.objects.create_user(
            phone="9400000003",
            password="AdminStrong@123",
            first_name="Admin",
            role="ADMIN",
            is_active=True,
            is_verified=True,
        )
        client = APIClient()
        login = client.post(
            "/api/auth/login/",
            {"phone": "9400000003", "password": "AdminStrong@123"},
            format="json",
            HTTP_X_ARI_DEVICE_ID="device-a",
        )
        denied = client.post(
            "/api/auth/admin/mfa/verify/",
            {
                "challenge": login.data["challenge"],
                "otp": memory_outbox[-1]["otp"],
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="device-b",
        )
        self.assertEqual(denied.status_code, 403)

    def test_customer_cannot_change_operational_ro_fields(self):
        user = User.objects.create_user(
            phone="9400000004",
            password="CustomerStrong@123",
            first_name="Customer",
            role="CUSTOMER",
            is_active=True,
            is_verified=True,
        )
        customer = Customer.objects.create(
            user=user,
            name="Customer",
            phone=user.phone,
            address="Address",
            city="Mathura",
            state="UP",
            pincode="281001",
            ro_model="ARI Secure RO",
            is_active=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            "/api/customers/profile/",
            {
                "name": "Updated Customer",
                "ro_model": "Tampered Model",
                "is_active": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Updated Customer")
        self.assertEqual(customer.ro_model, "ARI Secure RO")
        self.assertTrue(customer.is_active)
