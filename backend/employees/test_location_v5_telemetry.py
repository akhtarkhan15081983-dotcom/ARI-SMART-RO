from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from attendance.models import Attendance
from tenancy.models import Company, CompanyMembership

from .location_models import EmployeeLocationPoint
from .location_telemetry import normalize_location_telemetry
from .models import EmployeeProfile


class LocationTelemetryNormalizerTests(TestCase):
    def test_server_derives_quality_from_accuracy(self):
        telemetry = normalize_location_telemetry({
            "accuracy": 12.5,
            "quality_label": "POOR",
            "speed_mps": 7.2,
            "heading": 360,
            "motion_state": "driving",
            "client_point_id": "android:123:456",
            "client_sequence": 42,
            "altitude": 182.4,
            "client_platform": "android",
        })
        self.assertEqual(telemetry["quality_label"], "EXCELLENT")
        self.assertEqual(telemetry["motion_state"], "DRIVING")
        self.assertEqual(telemetry["heading_degrees"], 0.0)
        self.assertEqual(telemetry["client_sequence"], 42)

    def test_invalid_optional_values_do_not_break_legacy_contract(self):
        telemetry = normalize_location_telemetry({
            "speed_mps": -10,
            "heading": 999,
            "client_point_id": "contains spaces and is rejected",
            "client_platform": "desktop",
        })
        self.assertIsNone(telemetry["speed_mps"])
        self.assertIsNone(telemetry["heading_degrees"])
        self.assertIsNone(telemetry["client_point_id"])
        self.assertEqual(telemetry["client_platform"], "")
        self.assertEqual(telemetry["motion_state"], "UNKNOWN")


class LocationV5TelemetryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Fleet Telemetry Test Company",
            slug="fleet-telemetry-test-company",
            phone="9333333300",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.user = User.objects.create_user(
            phone="9333333301",
            password="Test@12345",
            first_name="Fleet",
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
            employee_id="EMP-V5-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("25000.00"),
            is_active=True,
        )
        self.now = timezone.now().replace(microsecond=0)
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            check_in=self.now - timedelta(hours=1),
            status="PRESENT",
        )
        self.client.force_authenticate(user=self.user)

    def _telemetry_point(self, captured_at=None, point_id="android:1001"):
        return {
            "live_latitude": 27.1491234,
            "live_longitude": 78.0451234,
            "captured_at": (captured_at or self.now).isoformat(),
            "accuracy": 9.5,
            "source": "FRESH_HIGH_ACCURACY",
            "speed_mps": 6.3,
            "heading": 87.0,
            "motion_state": "DRIVING",
            "quality_label": "POOR",
            "client_point_id": point_id,
            "client_sequence": 1001,
            "altitude": 176.2,
            "client_platform": "android",
        }

    def test_live_endpoint_persists_enriched_raw_point(self):
        response = self.client.post(
            "/api/employees/live-location/",
            self._telemetry_point(),
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        point = EmployeeLocationPoint.objects.get(
            employee=self.employee,
            client_point_id="android:1001",
        )
        self.assertEqual(point.quality_label, "EXCELLENT")
        self.assertEqual(point.motion_state, "DRIVING")
        self.assertAlmostEqual(point.accuracy_m, 9.5)
        self.assertAlmostEqual(point.speed_mps, 6.3)
        self.assertAlmostEqual(point.heading_degrees, 87.0)
        self.assertEqual(point.client_sequence, 1001)
        self.assertEqual(point.client_platform, "android")

    def test_legacy_live_payload_still_works(self):
        response = self.client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": 27.1500000,
                "live_longitude": 78.0460000,
                "captured_at": self.now.isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(EmployeeLocationPoint.objects.filter(employee=self.employee).exists())

    def test_retried_batch_client_point_id_is_deduplicated(self):
        captured = self.now - timedelta(minutes=5)
        payload = {"points": [self._telemetry_point(captured, "android:queued:1")]}

        first = self.client.post(
            "/api/employees/live-location/batch/",
            payload,
            format="json",
        )
        second = self.client.post(
            "/api/employees/live-location/batch/",
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            EmployeeLocationPoint.objects.filter(
                employee=self.employee,
                client_point_id="android:queued:1",
            ).count(),
            1,
        )
