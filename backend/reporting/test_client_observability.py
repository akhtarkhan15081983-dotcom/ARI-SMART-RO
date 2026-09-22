from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from reporting.models import ClientErrorEvent
from tenancy.models import Company, CompanyMembership


class ClientObservabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Observability Company",
            slug="observability-company",
            phone="9444444441",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9444444442",
            password="StrongPass123!",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
        )
        self.engineer = User.objects.create_user(
            phone="9444444443",
            password="StrongPass123!",
            first_name="Engineer",
            role="ENGINEER",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.engineer,
            role="STAFF",
            is_active=True,
        )

    def test_authenticated_client_can_report_error_with_allowlisted_context(self):
        self.client.force_authenticate(user=self.engineer)
        response = self.client.post(
            "/api/reports/client-errors/",
            {
                "platform": "ANDROID",
                "app_version": "1.0.34",
                "app_build": "34",
                "error_type": "StateError",
                "message": "Example failure",
                "stack": "stack line 1\nstack line 2",
                "context": {
                    "screen": "Attendance",
                    "operation": "check-in",
                    "phase": "submit",
                    "password": "must-not-store",
                    "token": "must-not-store",
                },
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="obs-device-1",
        )

        self.assertEqual(response.status_code, 201)
        row = ClientErrorEvent.objects.get(pk=response.data["event_id"])
        self.assertEqual(row.company_id, self.company.id)
        self.assertEqual(row.user, self.engineer)
        self.assertEqual(row.device_id, "obs-device-1")
        self.assertEqual(row.context["screen"], "Attendance")
        self.assertNotIn("password", row.context)
        self.assertNotIn("token", row.context)

    def test_admin_reads_only_current_company_errors(self):
        ClientErrorEvent.objects.create(
            user=self.engineer,
            company_id=self.company.id,
            company_name=self.company.name,
            error_type="StateError",
            message="Mine",
        )
        other = Company.objects.create(
            name="Other Observability",
            slug="other-observability",
            phone="9444444444",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        ClientErrorEvent.objects.create(
            company_id=other.id,
            company_name=other.name,
            error_type="OtherError",
            message="Other tenant",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/reports/client-errors/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["message"], "Mine")

    def test_engineer_cannot_read_error_feed(self):
        self.client.force_authenticate(user=self.engineer)
        response = self.client.get("/api/reports/client-errors/")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_client_cannot_report_error(self):
        response = self.client.post(
            "/api/reports/client-errors/",
            {"message": "No auth"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
