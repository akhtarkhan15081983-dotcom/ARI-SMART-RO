from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from tenancy.models import Company, CompanyMembership


class WorkPlannerTenantSecurityTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Planner Tenant A",
            slug="planner-tenant-a",
            phone="9001000001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Planner Tenant B",
            slug="planner-tenant-b",
            phone="9001000002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.manager_a = User.objects.create_user(
            phone="9001000011",
            password="Strong@123",
            role="MANAGER",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.manager_a,
            role="MANAGER",
            is_active=True,
        )
        self.engineer_a = self._engineer(self.company_a, "9001000021", "PLAN-A")
        self.engineer_b = self._engineer(self.company_b, "9001000022", "PLAN-B")
        self.customer_a = self._customer(
            self.company_a, self.engineer_a, "9001000031", "Planner Customer A"
        )
        self.customer_b = self._customer(
            self.company_b, self.engineer_b, "9001000032", "Planner Customer B"
        )
        self.complaint_a = self._complaint(self.company_a, self.customer_a, self.engineer_a)
        self.complaint_b = self._complaint(self.company_b, self.customer_b, self.engineer_b)
        self.complaint_a.refresh_from_db()
        self.complaint_b.refresh_from_db()
        self.client = APIClient()
        self.client.force_authenticate(self.manager_a)

    def _engineer(self, company, phone, employee_id):
        user = User.objects.create_user(
            phone=phone,
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=company,
            user=user,
            role="STAFF",
            is_active=True,
        )
        return EmployeeProfile.objects.create(
            company=company,
            user=user,
            employee_id=employee_id,
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("20000.00"),
            is_active=True,
        )

    def _customer(self, company, engineer, phone, name):
        return Customer.objects.create(
            company=company,
            name=name,
            phone=phone,
            address="Planner address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI RO",
            assigned_engineer=engineer,
        )

    def _complaint(self, company, customer, engineer):
        return Complaint.objects.create(
            company=company,
            customer=customer,
            engineer=engineer,
            complaint_type="OTHER",
            description="Planner tenant scope",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )

    def test_calendar_exposes_only_active_company_work_and_engineers(self):
        month = timezone.localdate().strftime("%Y-%m")
        response = self.client.get(reverse("work-calendar"), {"month": month})
        self.assertEqual(response.status_code, 200)
        event_customers = {row["customer"]["id"] for row in response.data["events"]}
        employee_ids = {row["id"] for row in response.data["employees"]}
        self.assertIn(self.customer_a.id, event_customers)
        self.assertNotIn(self.customer_b.id, event_customers)
        self.assertIn(self.engineer_a.id, employee_ids)
        self.assertNotIn(self.engineer_b.id, employee_ids)

    def test_manager_cannot_reschedule_other_company_work(self):
        response = self.client.patch(
            reverse("work-reschedule"),
            {
                "event_key": f"JOB:{self.complaint_b.job_id}",
                "scheduled_at": (timezone.now() + timezone.timedelta(days=1)).isoformat(),
                "employee_id": self.engineer_a.id,
                "reason": "Must stay tenant scoped",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
