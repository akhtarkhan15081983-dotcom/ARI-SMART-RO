from decimal import Decimal

from rest_framework.test import APITestCase

from accounts.models import User
from customers.models import Customer
from partmaster.models import PartCategory, PartMaster
from products.models import ProductCategory, ROModel, ROModelPart

from .models import ROAsset, ROAssetMovement, ROStockAudit


QC_CHECKLIST = {
    "pump_run": True,
    "leakage_test": True,
    "smps": True,
    "membrane": True,
    "body_damage": True,
}


class ROAssetWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone="9999999991",
            password="StrongPass123!",
            role="ADMIN",
            is_active=True,
            is_verified=True,
        )
        self.client.force_authenticate(self.admin)
        self.category = ProductCategory.objects.create(name="Domestic RO", is_active=True)
        self.model = ROModel.objects.create(
            category=self.category,
            model_name="ARI Test RO",
            capacity="12 LPH",
            business_type="SALE",
            available_for_sale=True,
            available_for_rent=True,
            selling_price=Decimal("8500.00"),
            monthly_rent=Decimal("450.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("2400.00"),
            stock_quantity=0,
            is_active=True,
        )
        part_category = PartCategory.objects.create(name="Test Filters", is_active=True)
        self.standard_part = PartMaster.objects.create(
            name="Sediment Filter",
            code="TEST-SED",
            category=part_category,
            is_serialized=False,
            warranty_months=6,
            replacement_interval_days=180,
            is_active=True,
        )
        ROModelPart.objects.create(
            ro_model=self.model,
            part=self.standard_part,
            quantity=1,
            is_mandatory=True,
        )
        self.customer = Customer.objects.create(
            name="Test Customer",
            phone="9999999992",
            address="Test Address",
            city="Aligarh",
            state="Uttar Pradesh",
            pincode="202001",
            ro_model="",
            ownership_type="RENTAL",
        )

    def _qc_pass(self, asset, *, returned=False):
        payload = {
            "result": "PASS",
            "checklist": QC_CHECKLIST,
            "notes": "All checks passed",
        }
        if returned:
            payload.update({"cleaned": True, "sanitized": True})
        response = self.client.post(
            f"/api/assets/workflow/{asset.id}/qc/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        asset.refresh_from_db()
        return response

    def test_bulk_receive_creates_passports_but_stock_waits_for_qc(self):
        response = self.client.post(
            "/api/assets/workflow/receive/",
            {
                "ro_model": self.model.id,
                "serial_numbers": ["RO-T-001", "RO-T-002"],
                "purchase_invoice": "INV-50",
                "purchase_price": "5000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["received"], 2)
        self.model.refresh_from_db()
        self.assertEqual(self.model.stock_quantity, 0)
        self.assertEqual(ROAsset.objects.filter(status="WAREHOUSE").count(), 2)
        self.assertEqual(ROAssetMovement.objects.filter(action="RECEIVED").count(), 2)

        first = ROAsset.objects.get(serial_number="RO-T-001")
        self.assertTrue(first.bom_verified)
        self.assertEqual(first.qc_status, "PENDING")
        self._qc_pass(first)
        self.model.refresh_from_db()
        self.assertEqual(self.model.stock_quantity, 1)
        self.assertTrue(first.release_ready)

    def test_qc_requires_complete_checklist(self):
        asset = ROAsset.objects.create(ro_model=self.model, serial_number="RO-QC-001")
        bad = dict(QC_CHECKLIST)
        bad["leakage_test"] = False
        response = self.client.post(
            f"/api/assets/workflow/{asset.id}/qc/",
            {"result": "PASS", "checklist": bad},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        asset.refresh_from_db()
        self.assertEqual(asset.qc_status, "PENDING")

    def test_rental_allocate_return_qc_and_restock_is_atomic(self):
        asset = ROAsset.objects.create(
            ro_model=self.model,
            serial_number="RO-R-001",
            status="WAREHOUSE",
        )
        self._qc_pass(asset)

        allocated = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "RENT"},
            format="json",
        )
        self.assertEqual(allocated.status_code, 200, allocated.data)
        asset.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(asset.status, "ASSIGNED")
        self.assertEqual(asset.deployment_type, "RENT")
        self.assertEqual(asset.current_customer_id, self.customer.id)
        self.assertEqual(self.customer.ownership_type, "RENTAL")

        duplicate = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 409)

        returned = self.client.post(
            f"/api/assets/workflow/{asset.id}/return/",
            {"remarks": "Customer return"},
            format="json",
        )
        self.assertEqual(returned.status_code, 200)
        asset.refresh_from_db()
        self.assertEqual(asset.status, "RETURNED")
        self.assertEqual(asset.qc_status, "PENDING")

        blocked = self.client.post(
            f"/api/assets/workflow/{asset.id}/restock/",
            {"remarks": "Try without QC"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

        self._qc_pass(asset, returned=True)
        restocked = self.client.post(
            f"/api/assets/workflow/{asset.id}/restock/",
            {"remarks": "Return QC complete"},
            format="json",
        )
        self.assertEqual(restocked.status_code, 200, restocked.data)
        asset.refresh_from_db()
        self.model.refresh_from_db()
        self.assertEqual(asset.status, "WAREHOUSE")
        self.assertEqual(asset.deployment_type, "")
        self.assertIsNone(asset.current_customer_id)
        self.assertEqual(self.model.stock_quantity, 1)
        actions = list(ROAssetMovement.objects.filter(asset=asset).values_list("action", flat=True))
        self.assertIn("RENT_ALLOCATED", actions)
        self.assertIn("RENT_RETURNED", actions)
        self.assertIn("QC_PASSED", actions)
        self.assertIn("RESTOCKED", actions)

    def test_reservation_blocks_other_customer_but_allows_reserved_customer(self):
        other = Customer.objects.create(
            name="Other Customer",
            phone="9999999993",
            address="Other Address",
            city="Aligarh",
            state="Uttar Pradesh",
            pincode="202001",
            ro_model="",
            ownership_type="RENTAL",
        )
        asset = ROAsset.objects.create(ro_model=self.model, serial_number="RO-RES-001")
        self._qc_pass(asset)
        reserved = self.client.post(
            f"/api/assets/workflow/{asset.id}/reserve/",
            {"customer_id": self.customer.id, "minutes": 60},
            format="json",
        )
        self.assertEqual(reserved.status_code, 200, reserved.data)

        wrong = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": other.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 409)

        right = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(right.status_code, 200, right.data)
        asset.refresh_from_db()
        self.assertIsNone(asset.reserved_for_customer_id)

    def test_physical_stock_audit_detects_missing_ro(self):
        first = ROAsset.objects.create(ro_model=self.model, serial_number="RO-AUD-001")
        second = ROAsset.objects.create(ro_model=self.model, serial_number="RO-AUD-002")
        self._qc_pass(first)
        self._qc_pass(second)

        started = self.client.post(
            "/api/assets/workflow/audits/",
            {"notes": "Monthly audit"},
            format="json",
        )
        self.assertEqual(started.status_code, 201, started.data)
        audit_id = started.data["audit_id"]
        self.assertEqual(started.data["expected"], 2)

        scanned = self.client.post(
            f"/api/assets/workflow/audits/{audit_id}/scan/",
            {"code": first.qr_code or first.serial_number},
            format="json",
        )
        self.assertEqual(scanned.status_code, 200, scanned.data)

        completed = self.client.post(
            f"/api/assets/workflow/audits/{audit_id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(completed.status_code, 200, completed.data)
        self.assertEqual(completed.data["missing_count"], 1)
        self.assertIn(second.asset_id, completed.data["missing_assets"])
        self.assertEqual(ROStockAudit.objects.get(pk=audit_id).status, "COMPLETED")

    def test_sale_allocation_requires_release_ready_and_updates_customer(self):
        asset = ROAsset.objects.create(ro_model=self.model, serial_number="RO-S-001", status="WAREHOUSE")
        blocked = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)
        self._qc_pass(asset)
        response = self.client.post(
            f"/api/assets/workflow/{asset.id}/allocate/",
            {"customer_id": self.customer.id, "deployment_type": "SALE"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        asset.refresh_from_db()
        self.customer.refresh_from_db()
        self.model.refresh_from_db()
        self.assertEqual(asset.deployment_type, "SALE")
        self.assertEqual(self.customer.ownership_type, "PURCHASE")
        self.assertEqual(self.customer.ro_model, self.model.model_name)
        self.assertEqual(self.model.stock_quantity, 0)
