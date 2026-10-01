from datetime import date
from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from assets.models import ROAsset
from customers.models import Customer
from employees.models import EmployeeProfile
from products.models import ProductCategory, ROModel
from tenancy.models import Company, CompanyMembership


class WalkInInstallationAmountTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Walkin Install Company",
            slug="walkin-install-company",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.user = User.objects.create_user(
            phone="9222222201",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Installer",
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.user,
            role="STAFF",
            is_active=True,
        )
        self.employee = EmployeeProfile.objects.create(
            company=self.company,
            user=self.user,
            employee_id="EMP-INSTALL-1",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("25000"),
        )
        category = ProductCategory.objects.create(name="Installation Split Test")
        self.model = ROModel.objects.create(
            category=category,
            model_name="Split Test RO",
            capacity="12 LPH",
            business_type="RENT",
        )
        self.asset = ROAsset.objects.create(company=self.company, ro_model=self.model)
        self.client.force_authenticate(self.user)

    def test_three_thousand_is_split_into_600_installation_and_2400_security(self):
        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Amount Split Customer",
                "phone": "9333333301",
                "alternate_phone": "",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": self.asset.id,
                "total_amount_received": "3000",
                "monthly_rent": "300",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(pk=response.data["customer_id"])
        self.assertEqual(customer.installation_charge, Decimal("600.00"))
        self.assertEqual(customer.security_deposit, Decimal("2400.00"))

    def test_amount_below_600_is_rejected(self):
        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Low Amount Customer",
                "phone": "9333333302",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": self.asset.id,
                "total_amount_received": "500",
                "monthly_rent": "300",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Customer.objects.filter(phone="9333333302").exists())


    def test_walkin_binds_customer_and_job_to_active_company(self):
        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Tenant Bound Customer",
                "phone": "9333333303",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": self.asset.id,
                "total_amount_received": "3000",
                "monthly_rent": "300",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        customer = Customer.objects.get(pk=response.data["customer_id"])
        self.assertEqual(customer.company_id, self.company.id)
        self.assertEqual(customer.assigned_engineer_id, self.employee.id)
        job = customer.jobs.get(pk=response.data["job_id"])
        self.assertEqual(job.company_id, self.company.id)
        self.assertEqual(job.engineer_id, self.employee.id)

    def test_walkin_rejects_already_assigned_asset(self):
        existing = Customer.objects.create(
            company=self.company,
            name="Existing Customer",
            phone="9333333304",
            address="Existing",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Split Test RO",
        )
        self.asset.current_customer = existing
        self.asset.status = "INSTALLED"
        self.asset.save(update_fields=["current_customer", "status"])

        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Must Not Claim Asset",
                "phone": "9333333305",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": self.asset.id,
                "total_amount_received": "3000",
                "monthly_rent": "300",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(Customer.objects.filter(phone="9333333305").exists())


    def test_walkin_rejects_other_company_warehouse_asset(self):
        other_company = Company.objects.create(
            name="Other Walkin Company",
            slug="other-walkin-company",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        other_asset = ROAsset.objects.create(
            company=other_company,
            ro_model=self.model,
            serial_number="WALKIN-OTHER-TENANT-001",
            status="WAREHOUSE",
        )

        response = self.client.post(
            "/api/customers/walk-in/",
            {
                "name": "Wrong Tenant Asset Customer",
                "phone": "9333333306",
                "address": "Test Address",
                "area": "Test Area",
                "city": "Agra",
                "state": "Uttar Pradesh",
                "pincode": "282001",
                "ro_model": self.model.id,
                "asset_id": other_asset.id,
                "total_amount_received": "3000",
                "monthly_rent": "300",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(Customer.objects.filter(phone="9333333306").exists())
        other_asset.refresh_from_db()
        self.assertIsNone(other_asset.current_customer_id)
        self.assertEqual(other_asset.status, "WAREHOUSE")
