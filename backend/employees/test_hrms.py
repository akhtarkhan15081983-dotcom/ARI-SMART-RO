from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from assets.models import ROAsset
from attendance.models import Attendance, OvertimeRequest
from customers.models import Customer
from jobs.models import Job
from products.models import ProductCategory, ROModel
from tenancy.models import Company, CompanyMembership
from .hrms import calculate_payroll
from .models import EmployeeCareerMovement, EmployeeDocument, EmployeePenalty, EmployeeProfile, HRPolicy, PerformanceReview


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

    def test_late_penalty_and_admin_approved_hourly_overtime(self):
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=date(2026, 2, 28),
            check_in=self._aware(10, 30),
            check_out=self._aware(18, 30),
            regular_shift_end_at=self._aware(18, 30),
            regular_working_hours=Decimal("8"),
            working_hours=Decimal("8"),
            status="PRESENT",
        )
        OvertimeRequest.objects.create(
            attendance=attendance,
            requested_hours=Decimal("2"),
            approved_hours=Decimal("2"),
            reason="Urgent assigned work",
            status="COMPLETED",
            started_at=self._aware(18, 30),
            planned_end_at=self._aware(20, 30),
            ended_at=self._aware(20, 30),
            end_reason="AUTO_APPROVED_LIMIT",
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["payable_base"], Decimal("1000.00"))
        self.assertEqual(result["late_penalty"], Decimal("50.00"))
        self.assertEqual(result["overtime_hours"], Decimal("2.00"))
        self.assertEqual(result["overtime_amount"], Decimal("250.00"))
        self.assertEqual(result["net_salary"], Decimal("1200.00"))

    def test_short_regular_hours_reduce_payroll(self):
        Attendance.objects.create(
            employee=self.employee,
            date=date(2026, 2, 28),
            check_in=self._aware(10, 0),
            check_out=self._aware(16, 0),
            regular_shift_end_at=self._aware(18, 0),
            regular_working_hours=Decimal("6"),
            working_hours=Decimal("6"),
            status="PRESENT",
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["short_hours"], Decimal("2.00"))
        self.assertEqual(result["short_hours_deduction"], Decimal("250.00"))
        self.assertEqual(result["overtime_amount"], Decimal("0.00"))
        self.assertEqual(result["net_salary"], Decimal("750.00"))

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

    def test_single_date_full_leave_is_allowed_and_monthly_limit_is_two(self):
        self.client.force_authenticate(self.user)
        today = timezone.localdate()
        if today.month == 12:
            month_start = date(today.year + 1, 1, 1)
        else:
            month_start = date(today.year, today.month + 1, 1)

        for day in (2, 3):
            selected = month_start.replace(day=day).isoformat()
            response = self.client.post("/api/employees/hrms/leaves/", {
                "leave_type": "FULL_DAY",
                "start_date": selected,
                "end_date": selected,
                "reason": "Personal work",
            }, format="json")
            self.assertEqual(response.status_code, 201)

        selected = month_start.replace(day=4).isoformat()
        response = self.client.post("/api/employees/hrms/leaves/", {
            "leave_type": "FULL_DAY",
            "start_date": selected,
            "end_date": selected,
            "reason": "Extra leave",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only 2 full-day", response.data["detail"])

    def test_single_date_half_leave_is_allowed_and_monthly_limit_is_two(self):
        self.client.force_authenticate(self.user)
        today = timezone.localdate()
        if today.month == 12:
            month_start = date(today.year + 1, 1, 1)
        else:
            month_start = date(today.year, today.month + 1, 1)

        for day in (5, 6):
            selected = month_start.replace(day=day).isoformat()
            response = self.client.post("/api/employees/hrms/leaves/", {
                "leave_type": "HALF_DAY",
                "start_date": selected,
                "end_date": selected,
                "reason": "Half-day personal work",
            }, format="json")
            self.assertEqual(response.status_code, 201)

        selected = month_start.replace(day=7).isoformat()
        response = self.client.post("/api/employees/hrms/leaves/", {
            "leave_type": "HALF_DAY",
            "start_date": selected,
            "end_date": selected,
            "reason": "Extra half day",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only 2 half-day", response.data["detail"])

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
            employee=self.employee,
            date=date(2026, 2, 28),
            check_in=self._aware(10, 30),
            check_out=self._aware(18, 30),
            regular_shift_end_at=self._aware(18, 30),
            regular_working_hours=Decimal("8"),
            working_hours=Decimal("8"),
            status="PRESENT",
        )
        result = calculate_payroll(self.employee, date(2026, 2, 1))
        self.assertEqual(result["other_deductions"], Decimal("100.00"))
        self.assertEqual(result["overtime_amount"], Decimal("0.00"))
        self.assertEqual(result["net_salary"], Decimal("850.00"))
        self.assertEqual(result["snapshot"]["manual_penalty_ids"], [penalty.id])

class CorporateHrmsDashboardTests(HRMSPolicyTests):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            phone="9111111177",
            password="Strong@Test1",
            role="ADMIN",
            first_name="HR Admin",
        )

    def test_admin_dashboard_returns_corporate_workforce_and_approval_metrics(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/employees/hrms/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "CORPORATE")
        self.assertIn("workforce", response.data)
        self.assertIn("approvals", response.data)
        self.assertIn("payroll", response.data)
        self.assertIn("attendance", response.data)
        self.assertGreaterEqual(response.data["workforce"]["active_employees"], 1)


class CorporateCareerMovementTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ARI Corporate HR Test",
            slug="ari-corporate-hr-test",
            phone="9111111160",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9111111161",
            password="Strong@Test1",
            role="ADMIN",
            first_name="HR Admin",
            is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9111111162",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Aman",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-CORP-1",
            joining_date=date(2025, 1, 1),
            designation="ENGINEER",
            job_title="Engineer",
            department="Service",
            grade="L1",
            gender="MALE",
            salary=Decimal("20000.00"),
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.employee_user,
            role="STAFF",
            is_active=True,
        )
        self.client.force_authenticate(self.admin)

    def test_promotion_draft_and_approval_updates_profile_and_keeps_history(self):
        today = timezone.localdate().isoformat()
        created = self.client.post(
            f"/api/employees/manage/{self.employee.id}/career/",
            {
                "movement_type": "PROMOTION",
                "effective_date": today,
                "new_designation": "ENGINEER",
                "new_job_title": "Senior Engineer",
                "new_department": "Service",
                "new_grade": "L2",
                "new_salary": "25000.00",
                "reason": "Performance promotion",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        movement = EmployeeCareerMovement.objects.get(pk=created.data["id"])
        self.assertEqual(movement.status, "DRAFT")
        self.assertEqual(movement.old_job_title, "Engineer")
        self.assertEqual(movement.new_job_title, "Senior Engineer")

        approved = self.client.post(
            f"/api/employees/manage/{self.employee.id}/career/{movement.id}/action/",
            {"action": "APPROVE"},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)

        self.employee.refresh_from_db()
        movement.refresh_from_db()
        self.assertEqual(self.employee.job_title, "Senior Engineer")
        self.assertEqual(self.employee.grade, "L2")
        self.assertEqual(self.employee.salary, Decimal("25000.00"))
        self.assertEqual(movement.status, "APPROVED")
        self.assertEqual(movement.approved_by, self.admin)

    def test_future_dated_promotion_stays_draft_until_effective_date(self):
        future = (timezone.localdate() + timedelta(days=30)).isoformat()
        created = self.client.post(
            f"/api/employees/manage/{self.employee.id}/career/",
            {
                "movement_type": "PROMOTION",
                "effective_date": future,
                "new_designation": "ENGINEER",
                "new_job_title": "Senior Engineer",
                "new_salary": "25000.00",
                "reason": "Scheduled promotion",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        movement_id = created.data["id"]
        approved = self.client.post(
            f"/api/employees/manage/{self.employee.id}/career/{movement_id}/action/",
            {"action": "APPROVE"},
            format="json",
        )
        self.assertEqual(approved.status_code, 400)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.job_title, "Engineer")


class PerformanceAndDocumentComplianceTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="ARI HR Compliance Test",
            slug="ari-hr-compliance-test",
            phone="9111111150",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9111111151",
            password="Strong@Test1",
            role="ADMIN",
            first_name="Admin",
            is_verified=True,
        )
        self.employee_user = User.objects.create_user(
            phone="9111111152",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Engineer",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.employee_user,
            employee_id="EMP-COMP-1",
            joining_date=date(2025, 1, 1),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("20000"),
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.admin, role="OWNER", is_active=True
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.employee_user, role="STAFF", is_active=True
        )

    def test_admin_can_create_finalize_and_employee_acknowledge_review(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/employees/hrms/performance/",
            {
                "employee_id": self.employee.id,
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "goals_score": "90",
                "attendance_score": "95",
                "service_quality_score": "88",
                "customer_score": "92",
                "sales_score": "85",
                "strengths": "Customer handling",
                "improvement_plan": "Increase first-time-fix rate",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        review = PerformanceReview.objects.get(pk=created.data["id"])
        self.assertEqual(review.status, "SUBMITTED")
        self.assertEqual(review.overall_score, Decimal("90.00"))

        finalized = self.client.post(
            f"/api/employees/hrms/performance/{review.id}/action/",
            {"action": "FINALIZE"},
            format="json",
        )
        self.assertEqual(finalized.status_code, 200)

        self.client.force_authenticate(self.employee_user)
        acknowledged = self.client.post(
            f"/api/employees/hrms/performance/{review.id}/action/",
            {"action": "ACKNOWLEDGE"},
            format="json",
        )
        self.assertEqual(acknowledged.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.status, "ACKNOWLEDGED")

    def test_document_compliance_marks_expired_document(self):
        EmployeeDocument.objects.create(
            employee=self.employee,
            document_type="Driving Licence",
            document_number="DL-TEST",
            expiry_date=timezone.localdate() - timedelta(days=1),
            verified=True,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            f"/api/employees/hrms/documents/?employee_id={self.employee.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["documents"][0]["expiry_state"], "EXPIRED")
