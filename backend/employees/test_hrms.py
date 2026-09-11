from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from assets.models import ROAsset
from attendance.models import Attendance
from customers.models import Customer
from jobs.models import Job
from products.models import ProductCategory, ROModel
from .hrms import calculate_payroll
from .models import EmployeePenalty, EmployeeProfile, HRPolicy


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

    def test_unfinished_assigned_work_deducts_ten_rupees_per_day(self):
        category = ProductCategory.objects.create(name="HRMS Test RO")
        model = ROModel.objects.create(
            category=category, model_name="Test RO", capacity="12 LPH",
            business_type="RENT",
        )
        customer = Customer.objects.create(
            name="Delay Test", phone="9111111188", address="Agra",
            city="Agra", state="UP", pincode="282001", ro_model="Test RO",
        )
        asset = ROAsset.objects.create(ro_model=model, current_customer=customer)
        Job.objects.create(
            customer=customer, ro_asset=asset, engineer=self.employee,
            job_type="SERVICE", scheduled_date=timezone.make_aware(datetime(2026, 2, 26, 8, 0)),
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["snapshot"]["work_delay_penalty_days"], 1)
        self.assertEqual(result["snapshot"]["work_delay_penalty_amount"], "10.00")
        self.assertEqual(result["other_deductions"], Decimal("10.00"))
    def test_leave_requires_one_day_notice(self):
        self.client.force_authenticate(self.user)
        today = timezone.localdate().isoformat()
        response = self.client.post("/api/employees/hrms/leaves/", {
            "leave_type": "FULL_DAY", "start_date": today, "end_date": today,
            "reason": "Personal work",
        }, format="json")
        self.assertEqual(response.status_code, 400)

class EmployeePenaltyWorkflowTests(HRMSPolicyTests):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            phone="9111111199", password="Strong@Test1", role="ADMIN", first_name="Admin"
        )

    def test_admin_approval_is_audited_and_deducted_from_payroll(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post("/api/employees/hrms/penalties/", {
            "employee_id": self.employee.id,
            "penalty_date": "2026-02-28",
            "amount": "100.00",
            "reason": "Verified equipment damage",
        }, format="json")
        self.assertEqual(created.status_code, 201)
        penalty = EmployeePenalty.objects.get(pk=created.data["id"])
        self.assertEqual(penalty.status, "DRAFT")

        approved = self.client.post(
            f"/api/employees/hrms/penalties/{penalty.id}/action/",
            {"action": "APPROVE"},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        penalty.refresh_from_db()
        self.assertEqual(penalty.status, "APPROVED")
        self.assertEqual(penalty.approved_by, self.admin)

        Attendance.objects.create(
            employee=self.employee, date=date(2026, 2, 28), check_in=self._aware(10, 30),
            check_out=self._aware(20, 30), working_hours=Decimal("10"), status="PRESENT",
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["other_deductions"], Decimal("100.00"))
        self.assertEqual(result["net_salary"], Decimal("1100.00"))
        self.assertEqual(result["snapshot"]["manual_penalty_ids"], [penalty.id])