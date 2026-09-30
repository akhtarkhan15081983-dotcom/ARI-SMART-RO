from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from assets.models import ROAlarm, ROAsset
from customers.models import Customer
from products.models import ProductCategory, ROModel
from tenancy.models import Company, CompanyMembership

from .ro_parts_models import ROPartsInspection, ROPartsObservation


class AdminROPassportTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Passport Company",
            slug="passport-company",
            phone="9999900000",
        )
        self.admin = User.objects.create_user(
            phone="9000000101",
            password="AdminPass123!",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="ADMIN",
        )
        self.customer_user = User.objects.create_user(
            phone="9000000102",
            password="CustomerPass123!",
            first_name="Customer",
            role="CUSTOMER",
            is_verified=True,
        )
        self.customer = Customer.objects.create(
            company=self.company,
            user=self.customer_user,
            name="Digital RO Customer",
            phone=self.customer_user.phone,
            address="Test address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Master RO Model",
        )
        category = ProductCategory.objects.create(name="Passport Category")
        model = ROModel.objects.create(
            category=category,
            model_name="ARI Max RO",
            capacity="12 LPH",
            business_type="RENT",
            available_for_rent=True,
        )
        self.asset = ROAsset.objects.create(
            ro_model=model,
            serial_number="PASSPORT-001",
            status="INSTALLED",
            current_customer=self.customer,
        )
        inspection = ROPartsInspection.objects.create(
            ro_asset=self.asset,
            customer=self.customer,
            inspection_type="BASELINE",
            source="MANUAL",
            status="CONFIRMED",
            confirmed_at=timezone.now(),
            created_by=self.admin,
        )
        ROPartsObservation.objects.create(
            inspection=inspection,
            part_key="sediment_filter",
            part_name="Sediment Filter",
            confidence=1,
            confirmed=True,
            installed_on=timezone.localdate(),
            date_source="BASELINE_ASSUMED",
        )
        ROAlarm.objects.create(
            ro_asset=self.asset,
            alarm_type="FILTER_DUE",
            severity="HIGH",
            source="SYSTEM",
            title="RO filter change due",
        )
        self.client = APIClient()

    def test_admin_sees_customer_model_parts_and_active_alarm(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/jobs/admin/ro-parts-passports/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["customer_count"], 1)
        row = response.data["customers"][0]
        self.assertEqual(row["name"], "Digital RO Customer")
        self.assertEqual(len(row["assets"]), 1)
        asset = row["assets"][0]
        self.assertEqual(asset["ro_model"], "ARI Max RO")
        self.assertEqual(asset["parts"][0]["part_name"], "Sediment Filter")
        self.assertEqual(asset["active_alarm_count"], 1)

    def test_admin_registry_is_company_scoped(self):
        other_company = Company.objects.create(
            name="Other Company",
            slug="other-passport-company",
            phone="9999900001",
        )
        Customer.objects.create(
            company=other_company,
            name="Hidden Customer",
            phone="8111100000",
            address="Other address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Hidden RO",
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/jobs/admin/ro-parts-passports/")
        names = [row["name"] for row in response.data["customers"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Digital RO Customer", names)
        self.assertNotIn("Hidden Customer", names)

    def test_customer_cannot_open_admin_registry(self):
        self.client.force_authenticate(self.customer_user)
        response = self.client.get("/api/jobs/admin/ro-parts-passports/")
        self.assertEqual(response.status_code, 403)
