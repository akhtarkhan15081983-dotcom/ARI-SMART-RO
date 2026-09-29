from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import SystemAuditEvent, User
from employees.models import EmployeeProfile
from tenancy.models import Company

from .models import Attendance


class MockLocationAttendanceSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="ARI SMART RO",
            slug="ari-smart-ro",
        )
        self.user = User.objects.create_user(
            phone="9000099911",
            password="StrongStaff@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            company=self.company,
            employee_id="EMP-MOCK-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            attendance_device_id="device-a",
        )
        self.client.force_authenticate(user=self.user)

    def test_mocked_location_is_blocked_before_attendance_creation(self):
        response = self.client.post(
            "/api/attendance/check-in/",
            {
                "latitude": "27.149028",
                "longitude": "78.045000",
                "device_id": "device-a",
                "is_mocked": "true",
            },
            format="multipart",
            HTTP_X_ARI_DEVICE_ID="device-a",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "MOCK_LOCATION_DETECTED")
        self.assertFalse(Attendance.objects.filter(employee=self.employee).exists())

        event = SystemAuditEvent.objects.filter(
            action="ATTENDANCE_MOCK_LOCATION_BLOCKED",
            entity_type="EmployeeProfile",
            entity_id=str(self.employee.id),
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.actor_id, self.user.id)
        self.assertTrue(event.metadata["reported_is_mocked"])
