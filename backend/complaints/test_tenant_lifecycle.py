from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Customer
from employees.models import EmployeeProfile
from tenancy.models import Company, CompanyMembership

from .models import Complaint


class ComplaintLifecycleTenantSecurityTests(APITestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Complaint Tenant A",
            slug="complaint-tenant-a",
            phone="9000700001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Complaint Tenant B",
            slug="complaint-tenant-b",
            phone="9000700002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.office_a = User.objects.create_user(
            phone="9000700011",
            password="Strong@123",
            role="OFFICE",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.office_a,
            role="STAFF",
            is_active=True,
        )
        self.engineer_a = self._employee(
            self.company_a, "9000700021", "CMP-A"
        )
        self.engineer_b = self._employee(
            self.company_b, "9000700022", "CMP-B"
        )
        self.customer_a = Customer.objects.create(
            company=self.company_a,
            name="Complaint A Customer",
            phone="9000700031",
            address="A",
            city="Agra",
            state="UP",
            pincode="282001",
            ro_model="ARI RO",
            assigned_engineer=self.engineer_a,
        )
        self.customer_b = Customer.objects.create(
            company=self.company_b,
            name="Complaint B Customer",
            phone="9000700032",
            address="B",
            city="Agra",
            state="UP",
            pincode="282001",
            ro_model="ARI RO",
            assigned_engineer=self.engineer_b,
        )
        self.complaint_b = Complaint.objects.create(
            company=self.company_b,
            customer=self.customer_b,
            engineer=self.engineer_b,
            complaint_type="OTHER",
            description="Other tenant complaint",
            status="ASSIGNED",
        )
        self.client.force_authenticate(self.office_a)

    def _employee(self, company, phone, employee_id):
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
            salary=Decimal("20000"),
            is_active=True,
        )

    def test_office_cannot_start_other_company_complaint(self):
        response = self.client.patch(
            f"/api/complaints/{self.complaint_b.id}/start/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.complaint_b.refresh_from_db()
        self.assertEqual(self.complaint_b.status, "ASSIGNED")

    def test_office_cannot_resolve_other_company_complaint(self):
        response = self.client.patch(
            f"/api/complaints/{self.complaint_b.id}/resolve/",
            {"resolution": "Must not cross tenant"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.complaint_b.refresh_from_db()
        self.assertEqual(self.complaint_b.status, "ASSIGNED")
