from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import SmsGatewayDevice, User


@override_settings(DISABLE_AUTH_THROTTLING=True, ARI_SMS_GATEWAY_NUMBER="")
class SmsGatewaySetupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            phone="9000000001",
            password="AdminStrong@123",
            role="ADMIN",
            is_verified=True,
        )
        self.customer = User.objects.create_user(
            phone="9000000002",
            password="CustomerStrong@123",
            role="CUSTOMER",
            is_verified=False,
        )

    def test_admin_can_provision_gateway_and_start_sim_verification(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/auth/admin/sms-gateway/",
            {"phone_number": "9876543210", "name": "Office Android"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertIn("api_key", response.data["gateway"])
        self.assertEqual(
            SmsGatewayDevice.objects.filter(is_active=True).count(),
            1,
        )

        self.client.force_authenticate(user=None)
        started = self.client.post(
            "/api/auth/sim-verification/start/",
            {"phone": self.customer.phone, "new_password": "NewStrong@123"},
            format="json",
        )
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.data["destination_number"], "9876543210")
        self.assertTrue(started.data["sms_body"].startswith("ARI VERIFY "))

    def test_reprovisioning_revokes_previous_gateway(self):
        self.client.force_authenticate(self.admin)
        first = self.client.post(
            "/api/auth/admin/sms-gateway/",
            {"phone_number": "9876543210"},
            format="json",
        )
        second = self.client.post(
            "/api/auth/admin/sms-gateway/",
            {"phone_number": "9876543211"},
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(SmsGatewayDevice.objects.filter(is_active=True).count(), 1)
        active = SmsGatewayDevice.objects.get(is_active=True)
        self.assertEqual(active.phone_number, "9876543211")

    def test_non_admin_cannot_provision_gateway(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/api/auth/admin/sms-gateway/",
            {"phone_number": "9876543210"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
