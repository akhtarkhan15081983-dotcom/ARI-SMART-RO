from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from assets.models import ROAsset
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel


class WorkPlannerDedupTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            phone="9555500001",
            password="TestPassword123!",
            role="ENGINEER",
        )
        self.engineer = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="PLAN-ENG-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        category = ProductCategory.objects.create(name="Planner Test Category")
        model = ROModel.objects.create(
            category=category,
            model_name="Planner Test RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("1000.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("1000.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.customer = Customer.objects.create(
            name="Planner Customer",
            phone="8555500001",
            address="Planner Address",
            city="Aligarh",
            state="Uttar Pradesh",
            pincode="202001",
            ro_model="Planner Test RO",
            assigned_engineer=self.engineer,
        )
        ROAsset.objects.create(
            ro_model=model,
            serial_number="PLAN-ASSET-001",
            status="INSTALLED",
            current_customer=self.customer,
        )
        self.complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer,
            complaint_type="WATER_LEAKAGE",
            description="Planner dedup test",
            scheduled_date=timezone.now(),
            status="ASSIGNED",
        )
        self.complaint.refresh_from_db()
        self.assertIsNotNone(self.complaint.job_id)

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_linked_complaint_is_exposed_once_as_job_event(self):
        month = self.complaint.scheduled_date.strftime("%Y-%m")
        response = self.client.get(reverse("work-calendar"), {"month": month})
        self.assertEqual(response.status_code, 200)

        events = response.data["events"]
        keys = {row["key"] for row in events}

        self.assertIn(f"JOB:{self.complaint.job_id}", keys)
        self.assertNotIn(f"COMPLAINT:{self.complaint.id}", keys)

        related = [
            row for row in events
            if row["customer"]["id"] == self.customer.id
            and row["type"] in {"JOB", "COMPLAINT"}
        ]
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["type"], "JOB")
