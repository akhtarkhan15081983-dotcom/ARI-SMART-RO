from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from employees.models import EmployeeProfile

from .models import Attendance
from .security import OFFICE_LATITUDE, OFFICE_LONGITUDE


class OfflineAttendanceSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="9000099101",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Offline",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP-OFFLINE-1",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            salary=25000,
            face_enrolled_at=timezone.now(),
            attendance_device_id="offline-device-1",
        )
        self.client.force_authenticate(self.user)

    def _payload(self, **overrides):
        payload = {
            "action_id": "offline-test-action-0001",
            "action": "CHECK_IN",
            "captured_at": (timezone.now() - timedelta(minutes=5)).isoformat(),
            "latitude": str(OFFICE_LATITUDE),
            "longitude": str(OFFICE_LONGITUDE),
            "device_id": "offline-device-1",
            "is_mocked": "false",
            "selfie": SimpleUploadedFile(
                "selfie.jpg",
                b"fake-image-content-for-test",
                content_type="image/jpeg",
            ),
        }
        payload.update(overrides)
        return payload

    def test_offline_check_in_uses_captured_time_and_stays_pending_review(self):
        captured_at = timezone.now() - timedelta(minutes=7)
        response = self.client.post(
            "/api/attendance/offline-sync/",
            self._payload(captured_at=captured_at.isoformat()),
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        row = Attendance.objects.get(employee=self.employee)
        self.assertLess(abs((row.check_in - captured_at).total_seconds()), 1)
        self.assertEqual(row.identity_review_status, "PENDING")
        self.assertIn("OFFLINE_SYNC", row.remarks)

    def test_offline_check_in_retry_is_idempotent_for_same_day(self):
        first = self.client.post(
            "/api/attendance/offline-sync/",
            self._payload(),
            format="multipart",
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            "/api/attendance/offline-sync/",
            self._payload(action_id="offline-test-action-0002"),
            format="multipart",
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["already_applied"])
        self.assertEqual(Attendance.objects.filter(employee=self.employee).count(), 1)

    def test_mock_location_is_rejected_for_offline_sync(self):
        response = self.client.post(
            "/api/attendance/offline-sync/",
            self._payload(is_mocked="true"),
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "MOCK_LOCATION_DETECTED")
        self.assertFalse(Attendance.objects.filter(employee=self.employee).exists())

    def test_offline_check_out_uses_captured_time_before_eight_hour_limit(self):
        check_in = timezone.now() - timedelta(hours=2)
        row = Attendance.objects.create(
            employee=self.employee,
            date=timezone.localtime(check_in).date(),
            check_in=check_in,
            status="PRESENT",
        )
        captured_out = check_in + timedelta(hours=1, minutes=30)

        response = self.client.post(
            "/api/attendance/offline-sync/",
            {
                "action_id": "offline-test-checkout-0001",
                "action": "CHECK_OUT",
                "captured_at": captured_out.isoformat(),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertLess(abs((row.check_out - captured_out).total_seconds()), 1)
        self.assertEqual(row.checkout_reason, "MANUAL")
        self.assertFalse(row.auto_checked_out)

    def test_offline_check_out_can_close_previous_local_day_shift(self):
        local_tz = timezone.get_current_timezone()
        check_in = timezone.make_aware(
            datetime(2026, 9, 30, 23, 0, 0),
            local_tz,
        )
        captured_out = check_in + timedelta(hours=1, minutes=30)
        server_now = captured_out + timedelta(minutes=5)
        row = Attendance.objects.create(
            employee=self.employee,
            date=timezone.localtime(check_in).date(),
            check_in=check_in,
            status="PRESENT",
        )

        with patch("attendance.offline_views.timezone.now", return_value=server_now):
            response = self.client.post(
                "/api/attendance/offline-sync/",
                {
                    "action_id": "offline-cross-midnight-0001",
                    "action": "CHECK_OUT",
                    "captured_at": captured_out.isoformat(),
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.date, timezone.localtime(check_in).date())
        self.assertLess(abs((row.check_out - captured_out).total_seconds()), 1)
        self.assertEqual(row.checkout_reason, "MANUAL")
        self.assertFalse(row.auto_checked_out)

    def test_offline_action_older_than_24_hours_is_rejected(self):
        response = self.client.post(
            "/api/attendance/offline-sync/",
            self._payload(
                captured_at=(timezone.now() - timedelta(hours=25)).isoformat(),
            ),
            format="multipart",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "OFFLINE_ACTION_TOO_OLD")
