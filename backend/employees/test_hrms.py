from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from attendance.models import Attendance
from .hrms import calculate_payroll
from .models import EmployeeProfile, HRPolicy


class HRMSPolicyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="9111111101", password="Strong@Test1", role="ENGINEER", first_name="Engineer")
        self.employee = EmployeeProfile.objects.create(
            user=self.user, employee_id="EMP-TEST-1", joining_date=date(2026, 2, 28),
            designation="ENGINEER", gender="MALE", salary=Decimal("28000"),
        )
        HRPolicy.current()

    def _aware(self, hour, minute):
        return timezone.make_aware(datetime(2026, 2, 28, hour, minute))

    def test_late_penalty_and_hourly_overtime(self):
        Attendance.objects.create(
            employee=self.employee, date=date(2026, 2, 28), check_in=self._aware(10, 30),
            check_out=self._aware(20, 30), working_hours=Decimal("10"), status="PRESENT",
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["payable_base"], Decimal("1000.00"))
        self.assertEqual(result["late_penalty"], Decimal("50.00"))
        self.assertEqual(result["overtime_amount"], Decimal("250.00"))
        self.assertEqual(result["net_salary"], Decimal("1200.00"))

    def test_after_noon_is_half_day_without_double_late_penalty(self):
        Attendance.objects.create(
            employee=self.employee, date=date(2026, 2, 28), check_in=self._aware(12, 5),
            check_out=self._aware(18, 5), working_hours=Decimal("6"), status="PRESENT",
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["late_penalty"], Decimal("0.00"))
        self.assertEqual(result["half_day_deduction"], Decimal("500.00"))
        self.assertEqual(result["net_salary"], Decimal("500.00"))

    def test_leave_requires_one_day_notice(self):
        self.client.force_authenticate(self.user)
        today = timezone.localdate().isoformat()
        response = self.client.post("/api/employees/hrms/leaves/", {
            "leave_type": "FULL_DAY", "start_date": today, "end_date": today,
            "reason": "Personal work",
        }, format="json")
        self.assertEqual(response.status_code, 400)
