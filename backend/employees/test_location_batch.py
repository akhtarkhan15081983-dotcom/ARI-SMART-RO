from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from attendance.models import Attendance
from tenancy.models import Company, CompanyMembership

from .location_models import EmployeeLocationPoint
from .models import EmployeeProfile


class EmployeeLocationBatchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Offline Route Test Company",
            slug="offline-route-test-company",
            phone="9222222200",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.user = User.objects.create_user(
            phone="9222222201",
            password="Test@12345",
            first_name="Offline",
            last_name="Engineer",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.user,
            role="STAFF",
            is_active=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.user,
            employee_id="EMP-OFFLINE-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )
        self.now = timezone.now().replace(microsecond=0)
        first_payload_point = self.now - timedelta(minutes=30)
        self.attendance = Attendance.objects.create(
            employee=self.employee,
            # Delayed GPS points may legitimately belong to the previous local
            # calendar day when a batch is uploaded shortly after midnight.
            date=timezone.localtime(first_payload_point).date(),
            check_in=self.now - timedelta(hours=2),
            status="PRESENT",
        )
        self.client.force_authenticate(user=self.user)

    def _payload(self):
        return {
            "points": [
                {
                    "live_latitude": 27.149,
                    "live_longitude": 78.045,
                    "accuracy": 8.0,
                    "captured_at": (self.now - timedelta(minutes=30)).isoformat(),
                },
                {
                    "live_latitude": 27.150,
                    "live_longitude": 78.046,
                    "accuracy": 7.0,
                    "captured_at": (self.now - timedelta(minutes=29)).isoformat(),
                },
            ]
        }

    def test_batch_persists_delayed_points_without_rolling_back_live_marker(self):
        self.employee.last_latitude = Decimal("27.2000000")
        self.employee.last_longitude = Decimal("78.1000000")
        self.employee.last_location_updated = self.now
        self.employee.is_online = True
        self.employee.save(
            update_fields=[
                "last_latitude",
                "last_longitude",
                "last_location_updated",
                "is_online",
            ]
        )

        response = self.client.post(
            "/api/employees/live-location/batch/",
            self._payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["accepted_count"], 2)
        self.assertEqual(response.data["rejected_count"], 0)
        self.assertEqual(
            EmployeeLocationPoint.objects.filter(employee=self.employee).count(),
            3,
        )

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.last_location_updated, self.now)
        self.assertEqual(self.employee.last_latitude, Decimal("27.2000000"))
        self.assertEqual(self.employee.last_longitude, Decimal("78.1000000"))

    def test_retried_batch_is_idempotent(self):
        first = self.client.post(
            "/api/employees/live-location/batch/",
            self._payload(),
            format="json",
        )
        second = self.client.post(
            "/api/employees/live-location/batch/",
            self._payload(),
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            EmployeeLocationPoint.objects.filter(employee=self.employee).count(),
            2,
        )

    def test_point_outside_attendance_window_is_rejected(self):
        self.attendance.check_out = self.now - timedelta(hours=1)
        self.attendance.save(update_fields=["check_out"])
        payload = {
            "points": [
                {
                    "live_latitude": 27.149,
                    "live_longitude": 78.045,
                    "captured_at": (self.now - timedelta(minutes=30)).isoformat(),
                }
            ]
        }

        response = self.client.post(
            "/api/employees/live-location/batch/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["accepted_count"], 0)
        self.assertEqual(response.data["rejected"]["outside_shift"], 1)
        self.assertFalse(EmployeeLocationPoint.objects.filter(employee=self.employee).exists())
