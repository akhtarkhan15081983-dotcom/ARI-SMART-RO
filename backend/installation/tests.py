from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from assets.models import ROAsset
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel
from tenancy.models import Company, CompanyMembership

from .models import Installation


class InstallationTenantSecurityTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Installation Tenant A",
            slug="installation-tenant-a",
            phone="9000900001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Installation Tenant B",
            slug="installation-tenant-b",
            phone="9000900002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.office_a = User.objects.create_user(
            phone="9000900011",
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
        self.engineer_a = self._employee(self.company_a, "9000900021", "INS-A")
        self.engineer_b = self._employee(self.company_b, "9000900022", "INS-B")

        category = ProductCategory.objects.create(name="Installation Tenant Test")
        self.ro_model = ROModel.objects.create(
            category=category,
            model_name="Installation Tenant RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("900.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("0.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.customer_a = self._customer(self.company_a, "9000900031", "Customer A")
        self.customer_b = self._customer(self.company_b, "9000900032", "Customer B")
        self.asset_a = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="INS-TENANT-A",
            status="INSTALLED",
            current_customer=self.customer_a,
        )
        self.asset_b = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="INS-TENANT-B",
            status="INSTALLED",
            current_customer=self.customer_b,
        )
        self.installation_a = Installation.objects.create(
            customer=self.customer_a,
            engineer=self.engineer_a,
            ro_asset=self.asset_a,
            business_type="RENT",
            scheduled_date=timezone.now(),
        )
        self.installation_b = Installation.objects.create(
            customer=self.customer_b,
            engineer=self.engineer_b,
            ro_asset=self.asset_b,
            business_type="RENT",
            scheduled_date=timezone.now(),
        )
        self.client = APIClient()
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
            salary=Decimal("20000.00"),
            is_active=True,
        )

    def _customer(self, company, phone, name):
        return Customer.objects.create(
            company=company,
            name=name,
            phone=phone,
            address="Test address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Installation Tenant RO",
        )

    def test_staff_list_contains_only_active_company_installations(self):
        response = self.client.get("/api/installations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {row["id"] for row in response.data},
            {self.installation_a.id},
        )

    def test_staff_cannot_update_other_company_installation(self):
        response = self.client.patch(
            f"/api/installations/{self.installation_b.id}/update/",
            {"remarks": "Cross tenant mutation"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.installation_b.refresh_from_db()
        self.assertNotEqual(self.installation_b.remarks, "Cross tenant mutation")

    def test_staff_cannot_create_installation_for_other_company(self):
        response = self.client.post(
            "/api/installations/create/",
            {
                "customer": self.customer_b.id,
                "engineer": self.engineer_b.id,
                "ro_asset": self.asset_b.id,
                "business_type": "RENT",
                "scheduled_date": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
