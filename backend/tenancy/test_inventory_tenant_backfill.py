import io
import json
from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from employees.models import EmployeeProfile
from inventory.models import EngineerBagItem, InventoryItem, PartRequest
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.inventory_tenant_backfill import build_inventory_ownership_plan
from tenancy.models import Company, CompanyMembership


class InventoryTenantOwnershipBackfillTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Warehouse A", slug="warehouse-a", phone="9000000101"
        )
        self.company_b = Company.objects.create(
            name="Warehouse B", slug="warehouse-b", phone="9000000102"
        )
        self.verifier = User.objects.create_user(
            phone="9111111201", password="Strong@123", role="ADMIN", is_active=True
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.verifier,
            role="ADMIN",
            is_active=True,
        )
        engineer_user_a = User.objects.create_user(
            phone="9111111202", password="Strong@123", role="ENGINEER", is_active=True
        )
        engineer_user_b = User.objects.create_user(
            phone="9111111203", password="Strong@123", role="ENGINEER", is_active=True
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=engineer_user_a,
            employee_id="INV-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=engineer_user_b,
            employee_id="INV-B",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        category = PartCategory.objects.create(name="Filters")
        self.part = PartMaster.objects.create(
            name="Sediment Filter", code="SED-TEST", category=category
        )
        self.supplier = Supplier.objects.create(name="Safe Supplier")
        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_number="INV-TENANT-001",
            invoice_date=date(2026, 9, 1),
            verified_by=self.verifier,
        )
        self.purchase_item = PurchaseItem.objects.create(
            purchase=self.purchase,
            part=self.part,
            quantity=1,
            purchase_price=Decimal("100.00"),
        )
        self.inventory = InventoryItem.objects.create(
            purchase_item=self.purchase_item,
            part=self.part,
            status="IN_STOCK",
        )
        self.part_request = PartRequest.objects.create(
            engineer=self.engineer_a,
            part=self.part,
            quantity=1,
        )

    def _decisions(self):
        return {(row.model, row.pk): row for row in build_inventory_ownership_plan()}

    def test_plan_resolves_purchase_chain_without_phone_inference(self):
        rows = self._decisions()
        self.assertEqual(rows[("Supplier", self.supplier.pk)].company_id, self.company_a.id)
        self.assertEqual(rows[("Purchase", self.purchase.pk)].company_id, self.company_a.id)
        self.assertEqual(rows[("PurchaseItem", self.purchase_item.pk)].company_id, self.company_a.id)
        self.assertEqual(rows[("InventoryItem", self.inventory.pk)].company_id, self.company_a.id)
        self.assertEqual(rows[("PartRequest", self.part_request.pk)].company_id, self.company_a.id)

    def test_cross_company_bag_conflicts_with_purchase_ownership(self):
        bag = EngineerBagItem.objects.create(
            engineer=self.engineer_b,
            inventory_item=self.inventory,
        )
        rows = self._decisions()
        inventory_decision = rows[("InventoryItem", self.inventory.pk)]
        bag_decision = rows[("EngineerBagItem", bag.pk)]
        self.assertEqual(inventory_decision.status, "CONFLICT")
        self.assertIsNone(inventory_decision.company_id)
        self.assertEqual(bag_decision.status, "CONFLICT")
        self.assertIsNone(bag_decision.company_id)

    def test_unresolved_supplier_stays_unresolved(self):
        orphan = Supplier.objects.create(name="Unresolved Supplier")
        rows = self._decisions()
        self.assertEqual(rows[("Supplier", orphan.pk)].status, "UNRESOLVED")
        self.assertIsNone(rows[("Supplier", orphan.pk)].company_id)

    def test_command_defaults_to_dry_run_and_writes_nothing(self):
        stdout = io.StringIO()
        call_command("backfill_inventory_tenant_ownership", stdout=stdout)
        payload = json.loads(stdout.getvalue().strip().splitlines()[-1])
        self.assertEqual(payload["mode"], "DRY_RUN")
        self.assertEqual(payload["applied_count"], 0)
        self.purchase.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertIsNone(self.purchase.company_id)
        self.assertIsNone(self.inventory.company_id)

    def test_apply_writes_only_resolved_rows(self):
        stdout = io.StringIO()
        call_command("backfill_inventory_tenant_ownership", "--apply", stdout=stdout)
        payload = json.loads(stdout.getvalue().strip().splitlines()[-1])
        self.assertEqual(payload["mode"], "APPLY")
        self.purchase.refresh_from_db()
        self.purchase_item.refresh_from_db()
        self.inventory.refresh_from_db()
        self.part_request.refresh_from_db()
        self.assertEqual(self.purchase.company_id, self.company_a.id)
        self.assertEqual(self.purchase_item.company_id, self.company_a.id)
        self.assertEqual(self.inventory.company_id, self.company_a.id)
        self.assertEqual(self.part_request.company_id, self.company_a.id)
