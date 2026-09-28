from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient
from django.test import TestCase

from accounts.models import User
from attendance.models import Attendance
from employees.models import EmployeeProfile, HRPolicy
from tenancy.models import Company, CompanyMembership


class AttendanceDeviceReliabilityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ARI SMART RO",
            slug="ari-smart-ro-test",
            phone="9999999999",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9000001101",
            password="Strong@Test1",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9000001102",
            password="Strong@Test1",
            first_name="Husnain",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.employee_user.active_login_device_id = "old-login-phone"
        self.employee_user.login_device_bound_at = timezone.now()
        self.employee_user.save(
            update_fields=["active_login_device_id", "login_device_bound_at"]
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-DEVICE-1",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("24000"),
            attendance_device_id="old-attendance-phone",
            face_enrolled_at=timezone.now(),
            face_enrollment_verified=True,
            face_enrollment_allowed=False,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.employee_user,
            role="STAFF",
            is_active=True,
        )
        HRPolicy.current()

    def test_admin_allow_reenrollment_resets_both_device_bindings(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.post(
            f"/api/employees/{self.employee.id}/face-enrollment-control/",
            {"action": "allow_reenrollment"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.employee_user.refresh_from_db()
        self.assertEqual(self.employee_user.active_login_device_id, "")
        self.assertEqual(self.employee_user.previous_login_device_id, "old-login-phone")
        self.assertEqual(self.employee.attendance_device_id, "")
        self.assertTrue(self.employee.face_enrollment_allowed)
        self.assertFalse(self.employee.face_enrollment_verified)
        self.assertFalse(response.data["login_device_bound"])
        self.assertFalse(response.data["attendance_device_bound"])

    def test_live_location_reconciles_and_stops_after_eight_hour_shift(self):
        check_in = timezone.now() - timedelta(hours=9)
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.localdate(),
            check_in=check_in,
            status="PRESENT",
        )
        self.employee.is_online = True
        self.employee.save(update_fields=["is_online"])

        client = APIClient()
        client.force_authenticate(self.employee_user)
        response = client.post(
            "/api/employees/live-location/",
            {
                "live_latitude": "28.8386480",
                "live_longitude": "78.7733280",
                "accuracy": "10",
                "captured_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        attendance.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertTrue(attendance.auto_checked_out)
        self.assertEqual(attendance.checkout_reason, "AUTO_8_HOURS")
        self.assertEqual(attendance.check_out, check_in + timedelta(hours=8))
        self.assertEqual(attendance.working_hours, Decimal("8.00"))
        self.assertFalse(self.employee.is_online)
        self.assertFalse(response.data["shift_active"])
        self.assertTrue(response.data["auto_checked_out"])
