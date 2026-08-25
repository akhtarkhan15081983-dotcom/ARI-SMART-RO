from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from attendance.models import Attendance
from customers.models import Customer, CustomerRentHistory, CustomerRentPayment
from employees.models import EmployeeProfile


class ReportingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            phone="9000000101",
            password="StrongPass123!",
            role="ADMIN",
            first_name="Admin",
        )
        self.customer_user = User.objects.create_user(
            phone="9000000102",
            password="StrongPass123!",
            role="CUSTOMER",
            first_name="Customer",
        )
        self.engineer_user = User.objects.create_user(
            phone="9000000103",
            password="StrongPass123!",
            role="ENGINEER",
            first_name="Ravi",
            last_name="Kumar",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.engineer_user,
            employee_id="EMP-TEST-001",
            gender="MALE",
            joining_date=date(2025, 1, 1),
            designation="ENGINEER",
        )
        self.customer = Customer.objects.create(
            name="Test Customer",
            phone="9000000104",
            address="Test Address",
            city="Bareilly",
            state="Uttar Pradesh",
            pincode="243001",
            ro_model="ARI Test RO",
            monthly_rent=Decimal("1000.00"),
        )
        rent_history = CustomerRentHistory.objects.create(
            customer=self.customer,
            rent_month=date(2026, 8, 1),
            expected_rent=Decimal("1000.00"),
            paid_amount=Decimal("700.00"),
        )
        CustomerRentPayment.objects.create(
            customer=self.customer,
            rent_history=rent_history,
            amount=Decimal("700.00"),
            payment_date=date(2026, 8, 20),
            payment_mode="UPI",
            collected_by=self.engineer,
        )
        Attendance.objects.create(
            employee=self.engineer,
            date=date(2026, 8, 25),
            status="PRESENT",
            working_hours=Decimal("8.00"),
        )

    def test_reports_require_authentication(self):
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, 401)

    def test_customer_cannot_view_business_reports(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get("/api/reports/summary/")
        self.assertEqual(response.status_code, 403)

    def test_monthly_report_aggregates_rent_and_attendance(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            "/api/reports/summary/",
            {"period": "monthly", "date": "2026-08-25"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period"]["start"], "2026-08-01")
        self.assertEqual(response.data["period"]["end"], "2026-08-31")
        self.assertEqual(response.data["rent"]["summary"]["expected"], "1000.00")
        self.assertEqual(response.data["rent"]["summary"]["paid"], "700.00")
        self.assertEqual(response.data["rent"]["summary"]["outstanding"], "300.00")
        self.assertEqual(response.data["attendance"]["summary"]["present"], 1)
        self.assertEqual(response.data["attendance"]["summary"]["working_hours"], "8.00")

    def test_all_standard_periods_are_supported(self):
        self.client.force_authenticate(self.admin)
        expected = {
            "daily": ("2026-08-25", "2026-08-25"),
            "weekly": ("2026-08-24", "2026-08-30"),
            "monthly": ("2026-08-01", "2026-08-31"),
            "quarterly": ("2026-07-01", "2026-09-30"),
            "halfyearly": ("2026-07-01", "2026-12-31"),
            "annual": ("2026-01-01", "2026-12-31"),
        }
        for period, dates in expected.items():
            with self.subTest(period=period):
                response = self.client.get(
                    "/api/reports/summary/",
                    {"period": period, "date": "2026-08-25"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["period"]["start"], dates[0])
                self.assertEqual(response.data["period"]["end"], dates[1])

    def test_custom_period_and_excel_export(self):
        self.client.force_authenticate(self.admin)
        params = {
            "period": "custom",
            "start": "2026-08-01",
            "end": "2026-08-25",
        }
        summary = self.client.get("/api/reports/summary/", params)
        self.assertEqual(summary.status_code, 200)

        export = self.client.get("/api/reports/export/", params)
        self.assertEqual(export.status_code, 200)
        self.assertEqual(
            export["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertGreater(len(export.content), 1000)

    def test_invalid_period_is_rejected(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            "/api/reports/summary/",
            {"period": "fortnightly"},
        )
        self.assertEqual(response.status_code, 400)
