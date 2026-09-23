from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from employees.models import EmployeeProfile


class EmployeeDeviceIdentityMigrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="9300000001",
            password="Test@123",
            first_name="Device",
            last_name="Migration",
            role="ENGINEER",
            is_verified=True,
            active_login_device_id="canonical-device",
            login_device_bound_at=timezone.now() - timedelta(days=10),
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP-DEVICE-0001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
            face_enrolled_at=timezone.now() - timedelta(days=5),
            face_enrollment_verified=True,
            attendance_device_id="legacy-attendance-device",
        )
        self.client.force_authenticate(self.user)

    def _post(self, legacy="legacy-attendance-device", header="canonical-device"):
        return self.client.post(
            "/api/employees/device-identity/migrate/",
            {"legacy_attendance_device_id": legacy},
            format="json",
            HTTP_X_ARI_DEVICE_ID=header,
        )

    def test_same_installation_migrates_legacy_attendance_identity(self):
        response = self._post()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["migrated"])

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.attendance_device_id, "canonical-device")

    def test_wrong_legacy_identity_does_not_rebind_attendance(self):
        response = self._post(legacy="someone-elses-device")

        self.assertEqual(response.status_code, 409)
        self.employee.refresh_from_db()
        self.assertEqual(
            self.employee.attendance_device_id,
            "legacy-attendance-device",
        )

    def test_wrong_login_device_header_is_rejected(self):
        response = self._post(header="different-login-device")

        self.assertEqual(response.status_code, 403)
        self.employee.refresh_from_db()
        self.assertEqual(
            self.employee.attendance_device_id,
            "legacy-attendance-device",
        )

    def test_login_device_reset_after_enrollment_requires_admin_reenrollment(self):
        self.user.login_device_reset_at = timezone.now()
        self.user.save(update_fields=["login_device_reset_at"])

        response = self._post()

        self.assertEqual(response.status_code, 409)
        self.assertIn("Admin re-enrollment", response.data["message"])
        self.employee.refresh_from_db()
        self.assertEqual(
            self.employee.attendance_device_id,
            "legacy-attendance-device",
        )

    def test_already_unified_is_idempotent(self):
        self.employee.attendance_device_id = "canonical-device"
        self.employee.save(update_fields=["attendance_device_id"])

        response = self._post()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["migrated"])
