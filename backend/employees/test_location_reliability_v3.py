from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from attendance.models import Attendance
from tenancy.models import Company, CompanyMembership

from .device_health_security import _location_diagnosis
from .models import EmployeeProfile


class LocationReliabilityV3Tests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Location V3 Test Company",
            slug="location-v3-test-company",
            phone="9300000098",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.manager_user = User.objects.create_user(
            phone="9300000001",
            password="Test@123",
            first_name="Location",
            last_name="Manager",
            role="MANAGER",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.manager_user,
            role="MANAGER",
            is_active=True,
        )
        self.manager = EmployeeProfile.objects.create(
            company=self.company,
            user=self.manager_user,
            employee_id="EMP-LOC-MGR",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="MANAGER",
            salary=Decimal("40000.00"),
            is_active=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9300000002",
            password="Test@123",
            first_name="Field",
            last_name="Employee",
            role="ENGINEER",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.employee_user,
            role="STAFF",
            is_active=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-LOC-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
            is_online=True,
            last_latitude=Decimal("28.6139000"),
            last_longitude=Decimal("77.2090000"),
        )
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            check_in=timezone.now() - timedelta(hours=1),
            status="PRESENT",
        )
        self.client.force_authenticate(user=self.manager_user)

    def _employee_row(self):
        response = self.client.get("/api/employees/live-map/")
        self.assertEqual(response.status_code, 200)
        return next(row for row in response.data if row["id"] == self.employee.id)

    def test_checked_in_employee_is_warning_after_90_seconds(self):
        self.employee.last_location_updated = timezone.now() - timedelta(minutes=2)
        self.employee.save(update_fields=["last_location_updated"])

        row = self._employee_row()

        self.assertEqual(row["location_status"], "STALE")
        self.assertEqual(row["location_alert"], "WARNING")
        self.assertEqual(row["location_alert_reason"], "GPS_STALE")
        self.assertFalse(row["online"])

    def test_checked_in_employee_is_critical_after_three_minutes(self):
        self.employee.last_location_updated = timezone.now() - timedelta(minutes=4)
        self.employee.save(update_fields=["last_location_updated"])

        row = self._employee_row()

        self.assertEqual(row["location_status"], "LOCATION_MISSING")
        self.assertEqual(row["location_alert"], "CRITICAL")
        self.assertEqual(row["location_alert_reason"], "GPS_NOT_REFRESHED_3_MIN")
        self.assertFalse(row["online"])
        self.assertGreaterEqual(row["location_age_seconds"], 180)

    def test_device_health_diagnosis_prioritizes_actionable_location_causes(self):
        base = {
            "location_service_enabled": True,
            "location_permission": "GRANTED",
            "background_location_granted": True,
            "notification_permission_granted": True,
            "battery_optimization_ignored": True,
            "live_location_tracking": True,
            "pending_location_points": 0,
        }

        diagnosis = _location_diagnosis(
            {**base, "location_service_enabled": False}, "MISSING"
        )
        self.assertEqual(diagnosis["code"], "GPS_OFF")

        diagnosis = _location_diagnosis(
            {**base, "background_location_granted": False}, "MISSING"
        )
        self.assertEqual(diagnosis["code"], "BACKGROUND_LOCATION_DENIED")

        diagnosis = _location_diagnosis(
            {**base, "battery_optimization_ignored": False}, "STALE"
        )
        self.assertEqual(diagnosis["code"], "BATTERY_RESTRICTED")

        diagnosis = _location_diagnosis(
            {**base, "live_location_tracking": False}, "STALE"
        )
        self.assertEqual(diagnosis["code"], "TRACKING_SERVICE_STOPPED")

        diagnosis = _location_diagnosis(
            {**base, "pending_location_points": 5}, "STALE"
        )
        self.assertEqual(diagnosis["code"], "OFFLINE_POINTS_PENDING")
