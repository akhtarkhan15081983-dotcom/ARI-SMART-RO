from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import SystemAuditEvent, User
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
                "app_version": "1.0.48",
                "app_build": "48",
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
                "pending_attendance_actions": 4,
                "pending_location_points": 2,
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="device-health-test-1",
        )

        self.assertEqual(response.status_code, 200)
        row = EmployeeDeviceHealth.objects.get(employee=self.engineer)
        self.assertEqual(row.device_id, "device-health-test-1")
        self.assertEqual(row.app_version, "1.0.48")
        self.assertEqual(row.pending_job_actions, 3)
        self.assertEqual(row.pending_location_points, 2)
        self.assertTrue(row.background_location_granted)
        self.assertEqual(response.data["risk_level"], "CLEAR")
        self.assertEqual(response.data["pending_attendance_actions"], 4)
        self.assertIn("ATTENDANCE_PENDING[4]", row.last_error)

        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get("/api/employees/admin/device-health/")
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(
            admin_response.data[0]["health"]["pending_attendance_actions"],
            4,
        )
        self.assertNotIn(
            "ATTENDANCE_PENDING[",
            admin_response.data[0]["health"]["last_error"],
        )

    def test_risky_device_report_is_visible_and_audited(self):
        self.client.force_authenticate(user=self.engineer_user)
        response = self.client.post(
            "/api/employees/device-health/",
            {
                "platform": "ANDROID",
                "app_version": "1.0.48",
                "root_risk_detected": True,
                "emulator_detected": True,
                "mock_location_detected": True,
                "pending_attendance_actions": 2,
            },
            format="json",
            HTTP_X_ARI_DEVICE_ID="risky-device",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["risk_level"], "HIGH")
        self.assertEqual(
            set(response.data["security_risks"]),
            {"ROOT_RISK", "EMULATOR", "MOCK_LOCATION"},
        )
        row = EmployeeDeviceHealth.objects.get(employee=self.engineer)
        self.assertIn("SECURITY_RISK[", row.last_error)
        self.assertIn("ATTENDANCE_PENDING[2]", row.last_error)
        self.assertTrue(
            SystemAuditEvent.objects.filter(
                action="DEVICE_SECURITY_RISK_REPORTED",
                entity_id=str(row.id),
            ).exists()
        )

        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.get("/api/employees/admin/device-health/")
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response.data[0]["risk_level"], "HIGH")
        self.assertIn("ROOT_RISK", admin_response.data[0]["security_risks"])
        self.assertEqual(
            admin_response.data[0]["health"]["pending_attendance_actions"],
            2,
        )
        self.assertFalse(admin_response.data[0]["health"]["last_error"].startswith("SECURITY_RISK["))
        self.assertNotIn(
            "ATTENDANCE_PENDING[",
            admin_response.data[0]["health"]["last_error"],
        )

    def test_admin_can_view_company_device_health(self):
        EmployeeDeviceHealth.objects.create(
            employee=self.engineer,
            device_id="device-health-test-2",
            app_version="1.0.48",
            os_version="16",
            location_permission="GRANTED",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/employees/admin/device-health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["employee_code"], "EMP-HEALTH-001")
        self.assertEqual(response.data[0]["health"]["app_version"], "1.0.48")
        self.assertEqual(response.data[0]["health"]["pending_attendance_actions"], 0)
        self.assertIn(response.data[0]["status"], {"HEALTHY", "STALE"})
        self.assertEqual(response.data[0]["risk_level"], "CLEAR")

    def test_admin_device_health_hides_other_company_employee(self):
        other_company = Company.objects.create(
            name="Other Device Company",
            slug="other-device-company",
            phone="9777777777",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        other_user = User.objects.create_user(
            phone="9100000004",
            password="Test@12345",
            first_name="Other Device",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        other_employee = EmployeeProfile.objects.create(
            company=other_company,
            user=other_user,
            employee_id="EMP-OTHER-HEALTH",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )
        EmployeeDeviceHealth.objects.create(
            employee=other_employee,
            device_id="other-company-device",
            app_version="1.0.48",
            os_version="16",
            location_permission="GRANTED",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/employees/admin/device-health/")

        self.assertEqual(response.status_code, 200)
        employee_codes = {row["employee_code"] for row in response.data}
        self.assertIn("EMP-HEALTH-001", employee_codes)
        self.assertNotIn("EMP-OTHER-HEALTH", employee_codes)

    def test_admin_face_list_is_tenant_scoped(self):
        other_company = Company.objects.create(
            name="Other Company",
            slug="other-company-device-test",
            phone="9888888888",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        other_user = User.objects.create_user(
            phone="9100000003",
            password="Test@12345",
            first_name="Other",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        EmployeeProfile.objects.create(
            company=other_company,
            user=other_user,
            employee_id="EMP-OTHER-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/employees/admin/face-enrollments/")
        self.assertEqual(response.status_code, 200)
        codes = {row["employee_id"] for row in response.data}
        self.assertIn("EMP-HEALTH-001", codes)
        self.assertNotIn("EMP-OTHER-001", codes)

    def test_device_health_requires_authentication(self):
        response = self.client.post("/api/employees/device-health/", {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_admin_device_health_rejects_non_admin(self):
        self.client.force_authenticate(user=self.engineer_user)
        response = self.client.get("/api/employees/admin/device-health/")
        self.assertEqual(response.status_code, 403)
