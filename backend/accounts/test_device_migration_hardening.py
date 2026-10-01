from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuthSecurityEvent, User


class EmployeeDeviceMigrationHardeningTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="9000012345",
            password="DeviceStrong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.user.active_login_device_id = "phone-old"
        self.user.save(update_fields=["active_login_device_id"])

    def test_legacy_header_cannot_move_bound_employee_login_to_new_phone(self):
        response = self.client.post(
            "/api/auth/login/",
            {"phone": self.user.phone, "password": "DeviceStrong@123"},
            format="json",
            HTTP_X_ARI_DEVICE_ID="phone-new",
            HTTP_X_ARI_LEGACY_DEVICE_ID="phone-old",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "EMPLOYEE_DEVICE_ALREADY_BOUND")
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_login_device_id, "phone-old")
        self.assertTrue(
            AuthSecurityEvent.objects.filter(
                user=self.user,
                event_type="LOGIN_DEVICE_BLOCKED",
                details__reason="ADMIN_RESET_REQUIRED_FOR_NEW_PHONE",
            ).exists()
        )

    def test_existing_session_cannot_migrate_with_legacy_header(self):
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}",
            HTTP_X_ARI_DEVICE_ID="phone-new",
            HTTP_X_ARI_LEGACY_DEVICE_ID="phone-old",
        )

        response = self.client.post(
            "/api/auth/change-password/",
            {
                "old_password": "DeviceStrong@123",
                "new_password": "DeviceStrong@456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_login_device_id, "phone-old")
        self.assertTrue(self.user.check_password("DeviceStrong@123"))

    def test_admin_reset_state_allows_next_phone_to_bind_normally(self):
        self.user.previous_login_device_id = "phone-old"
        self.user.active_login_device_id = ""
        self.user.save(
            update_fields=["previous_login_device_id", "active_login_device_id"]
        )

        response = self.client.post(
            "/api/auth/login/",
            {"phone": self.user.phone, "password": "DeviceStrong@123"},
            format="json",
            HTTP_X_ARI_DEVICE_ID="phone-new",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.active_login_device_id, "phone-new")
