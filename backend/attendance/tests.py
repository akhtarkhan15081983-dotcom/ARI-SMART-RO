from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from employees.models import EmployeeProfile, HRPolicy
from .models import Attendance, OvertimeRequest
from .work_hours import recalculate_attendance

from .security import (
    OFFICE_LATITUDE,
    OFFICE_LONGITUDE,
    OFFICE_RADIUS_METERS,
    distance_from_office_meters,
    is_inside_office_geofence,
)


class OfficeGeofenceTests(SimpleTestCase):
    def test_office_coordinate_is_inside_geofence(self):
        self.assertTrue(
            is_inside_office_geofence(OFFICE_LATITUDE, OFFICE_LONGITUDE)
        )
        self.assertAlmostEqual(
            distance_from_office_meters(OFFICE_LATITUDE, OFFICE_LONGITUDE),
            0.0,
            places=3,
        )

    def test_point_about_40m_north_is_allowed(self):
        latitude = OFFICE_LATITUDE + (40.0 / 111_320.0)
        self.assertLess(
            distance_from_office_meters(latitude, OFFICE_LONGITUDE),
            OFFICE_RADIUS_METERS,
        )
        self.assertTrue(is_inside_office_geofence(latitude, OFFICE_LONGITUDE))

    def test_point_about_60m_north_is_rejected(self):
        latitude = OFFICE_LATITUDE + (60.0 / 111_320.0)
        self.assertGreater(
            distance_from_office_meters(latitude, OFFICE_LONGITUDE),
            OFFICE_RADIUS_METERS,
        )
        self.assertFalse(is_inside_office_geofence(latitude, OFFICE_LONGITUDE))


class WorkHoursAndOvertimeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee_user = User.objects.create_user(
            phone="9000000901",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Shift",
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            phone="9000000902",
            password="Strong@Test1",
            role="ADMIN",
            first_name="Admin",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.employee_user,
            employee_id="EMP-SHIFT-1",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("24000"),
        )
        HRPolicy.current()

    def _attendance(self, hours_ago=9):
        check_in = timezone.now() - timedelta(hours=hours_ago)
        return Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            check_in=check_in,
            status="PRESENT",
        )

    def test_regular_shift_auto_checks_out_at_exact_eight_hours(self):
        row = self._attendance(hours_ago=9)
        recalculate_attendance(row, now=timezone.now())
        row.refresh_from_db()

        expected_end = row.check_in + timedelta(hours=8)
        self.assertEqual(row.check_out, expected_end)
        self.assertTrue(row.auto_checked_out)
        self.assertEqual(row.checkout_reason, "AUTO_8_HOURS")
        self.assertEqual(row.regular_working_hours, Decimal("8.00"))
        self.assertEqual(row.overtime_working_hours, Decimal("0.00"))
        self.assertEqual(row.working_hours, Decimal("8.00"))

    def test_overtime_requires_admin_approval_before_start(self):
        row = self._attendance(hours_ago=9)
        recalculate_attendance(row)

        self.client.force_authenticate(self.employee_user)
        requested = self.client.post(
            "/api/attendance/overtime/",
            {"hours": "2", "reason": "Finish urgent customer jobs"},
            format="json",
        )
        self.assertEqual(requested.status_code, 201)
        request_row = OvertimeRequest.objects.get(attendance=row)
        self.assertEqual(request_row.status, "PENDING")

        blocked = self.client.post("/api/attendance/overtime/start/", {}, format="json")
        self.assertEqual(blocked.status_code, 403)

        self.client.force_authenticate(self.admin)
        approved = self.client.post(
            f"/api/attendance/admin/overtime/{request_row.id}/",
            {"action": "APPROVE", "approved_hours": "1.5", "note": "Approved for urgent work"},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)

        self.client.force_authenticate(self.employee_user)
        started = self.client.post("/api/attendance/overtime/start/", {}, format="json")
        self.assertEqual(started.status_code, 200)
        request_row.refresh_from_db()
        self.assertIsNotNone(request_row.started_at)
        self.assertEqual(request_row.approved_hours, Decimal("1.50"))

    def test_completed_approved_overtime_is_added_to_working_hours(self):
        row = self._attendance(hours_ago=11)
        shift_end = row.check_in + timedelta(hours=8)
        OvertimeRequest.objects.create(
            attendance=row,
            requested_hours=Decimal("2.00"),
            approved_hours=Decimal("2.00"),
            reason="Urgent work",
            status="COMPLETED",
            reviewed_by=self.admin,
            reviewed_at=shift_end,
            started_at=shift_end,
            planned_end_at=shift_end + timedelta(hours=2),
            ended_at=shift_end + timedelta(hours=2),
            end_reason="AUTO_APPROVED_LIMIT",
        )

        recalculate_attendance(row, now=shift_end + timedelta(hours=3))
        row.refresh_from_db()
        self.assertEqual(row.regular_working_hours, Decimal("8.00"))
        self.assertEqual(row.overtime_working_hours, Decimal("2.00"))
        self.assertEqual(row.working_hours, Decimal("10.00"))
