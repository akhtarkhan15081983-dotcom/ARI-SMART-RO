from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from tenancy.models import Company, CompanyMembership
from .models import EmployeeDeviceHealth, EmployeeProfile


class DeviceHealthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="ARI Smart RO",
            slug="ari-smart-ro-test",
            phone="9999999999",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9100000001",
            password="Test@12345",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="ADMIN",
            is_active=True,
        )

        self.engineer_user = User.objects.create_user(
            phone="9100000002",
            password="Test@12345",
            first_name="Engineer",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            company=self.company,
            user=self.engineer_user,
            employee_id="EMP-HEALTH-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )

    def test_employee_can_report_device_health(self):
        self.client.force_authenticate(user=self.engineer_user)
        response = self.client.post(
            "/api/employees/device-health/",
            {
                "platform": "ANDROID",
                "app_version": "1.0.34",
                "app_build": "34",
                "os_version": "16",
                "android_sdk": 36,
                "manufacturer": "Example",
                "model": "Phone",
                "low_memory_device": False,
                "memory_class_mb": 256,
                "total_memory_mb": 4096,
                "location_service_enabled": True,
                "location_permission": "GRANTED",
                "background_location_granted": True,
                "notification_permission_granted": True,
                "battery_optimization_ignored": True,
                "live_location_tracking": True,
                "pending_job_actions": 3,
                "pending_location_points": 2,
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="device-health-test-1",
        )

        self.assertEqual(response.status_code, 200)
        row = EmployeeDeviceHealth.objects.get(employee=self.engineer)
        self.assertEqual(row.device_id, "device-health-test-1")
        self.assertEqual(row.app_version, "1.0.34")
        self.assertEqual(row.pending_job_actions, 3)
        self.assertEqual(row.pending_location_points, 2)
        self.assertTrue(row.background_location_granted)

    def test_admin_can_view_company_device_health(self):
        EmployeeDeviceHealth.objects.create(
            employee=self.engineer,
            device_id="device-health-test-2",
            app_version="1.0.34",
            os_version="16",
            location_permission="GRANTED",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/employees/admin/device-health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["employee_code"], "EMP-HEALTH-001")
        self.assertEqual(response.data[0]["health"]["app_version"], "1.0.34")
        self.assertIn(response.data[0]["status"], {"HEALTHY", "STALE"})

    def test_device_health_requires_authentication(self):
        response = self.client.post("/api/employees/device-health/", {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_admin_device_health_rejects_non_admin(self):
        self.client.force_authenticate(user=self.engineer_user)
        response = self.client.get("/api/employees/admin/device-health/")
        self.assertEqual(response.status_code, 403)
