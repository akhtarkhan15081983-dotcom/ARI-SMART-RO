import json

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
        self.unassigned_customer = Customer.objects.create(
            company=self.company,
            name="Legacy Sale Customer",
            phone="9000000199",
            address="Legacy address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="Old handwritten model",
        )
        category = ProductCategory.objects.create(name="Passport Category")
        self.model = ROModel.objects.create(
            category=category,
            model_name="ARI Max RO",
            capacity="12 LPH",
            business_type="RENT",
            available_for_rent=True,
        )
        self.asset = ROAsset.objects.create(
            ro_model=self.model,
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
        self.assertEqual(response.data["customer_count"], 2)
        row = next(
            item
            for item in response.data["customers"]
            if item["name"] == "Digital RO Customer"
        )
        self.assertEqual(len(row["assets"]), 1)
        asset = row["assets"][0]
        self.assertEqual(asset["ro_model"], "ARI Max RO")
        self.assertEqual(asset["parts"][0]["part_name"], "Sediment Filter")
        self.assertEqual(asset["active_alarm_count"], 1)
        self.assertTrue(asset["manual_setup_allowed"])

        legacy = next(
            item
            for item in response.data["customers"]
            if item["name"] == "Legacy Sale Customer"
        )
        self.assertEqual(legacy["assets"], [])

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
        self.assertIn("Legacy Sale Customer", names)
        self.assertNotIn("Hidden Customer", names)

    def test_customer_cannot_open_admin_registry_or_setup(self):
        self.client.force_authenticate(self.customer_user)
        registry = self.client.get("/api/jobs/admin/ro-parts-passports/")
        options = self.client.get("/api/jobs/admin/ro-parts-passports/setup/")

        self.assertEqual(registry.status_code, 403)
        self.assertEqual(options.status_code, 403)

    def test_admin_can_initialise_legacy_sale_ro_baseline(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/jobs/admin/ro-parts-passports/setup/",
            {
                "customer_id": str(self.unassigned_customer.id),
                "ro_model_id": str(self.model.id),
                "serial_number": "LEGACY-SALE-001",
                "ownership_type": "PURCHASE",
                "sale_installation_date": "2026-04-01",
                "parts": json.dumps(
                    [
                        {"part_key": "sediment_filter"},
                        {"part_key": "ro_membrane"},
                        {"part_key": "booster_pump"},
                    ]
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        asset = ROAsset.objects.get(current_customer=self.unassigned_customer)
        self.assertEqual(asset.ro_model, self.model)
        self.assertEqual(asset.serial_number, "LEGACY-SALE-001")
        self.assertEqual(str(asset.purchase_date), "2026-04-01")

        self.unassigned_customer.refresh_from_db()
        self.assertEqual(self.unassigned_customer.ro_model, "ARI Max RO")
        self.assertEqual(self.unassigned_customer.ownership_type, "PURCHASE")
        self.assertEqual(
            str(self.unassigned_customer.installation_date),
            "2026-04-01",
        )

        inspection = ROPartsInspection.objects.get(ro_asset=asset)
        self.assertEqual(inspection.source, "MANUAL")
        self.assertEqual(inspection.status, "CONFIRMED")
        self.assertEqual(
            set(inspection.observations.values_list("part_key", flat=True)),
            {"sediment_filter", "ro_membrane", "booster_pump"},
        )

    def test_admin_can_correct_manual_baseline_before_automatic_history(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/jobs/admin/ro-parts-passports/setup/",
            {
                "customer_id": str(self.customer.id),
                "asset_id": str(self.asset.id),
                "ro_model_id": str(self.model.id),
                "serial_number": self.asset.serial_number,
                "ownership_type": "RENTAL",
                "parts": json.dumps(
                    [
                        {"part_key": "pre_carbon"},
                        {"part_key": "ro_membrane"},
                    ]
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200, response.data)
        inspection = ROPartsInspection.objects.get(ro_asset=self.asset)
        self.assertEqual(
            set(inspection.observations.values_list("part_key", flat=True)),
            {"pre_carbon", "ro_membrane"},
        )

    def test_admin_baseline_locks_after_automatic_history_starts(self):
        ROPartsInspection.objects.create(
            ro_asset=self.asset,
            customer=self.customer,
            inspection_type="REPLACEMENT",
            source="INVENTORY_JOB",
            status="CONFIRMED",
            confirmed_at=timezone.now(),
            created_by=self.admin,
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/jobs/admin/ro-parts-passports/setup/",
            {
                "customer_id": str(self.customer.id),
                "asset_id": str(self.asset.id),
                "ro_model_id": str(self.model.id),
                "serial_number": self.asset.serial_number,
                "ownership_type": "RENTAL",
                "parts": json.dumps([{"part_key": "sediment_filter"}]),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("locked", response.data["detail"].lower())

    def test_admin_cannot_initialise_customer_from_another_company(self):
        other_company = Company.objects.create(
            name="Other Setup Company",
            slug="other-setup-company",
            phone="9999900099",
        )
        hidden = Customer.objects.create(
            company=other_company,
            name="Hidden Setup Customer",
            phone="8111100099",
            address="Other address",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            ro_model="Hidden RO",
        )
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/jobs/admin/ro-parts-passports/setup/",
            {
                "customer_id": str(hidden.id),
                "ro_model_id": str(self.model.id),
                "serial_number": "CROSS-COMPANY-001",
                "ownership_type": "PURCHASE",
                "parts": json.dumps([{"part_key": "sediment_filter"}]),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            ROAsset.objects.filter(serial_number="CROSS-COMPANY-001").exists()
        )
