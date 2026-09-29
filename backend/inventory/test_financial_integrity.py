from datetime import date
from decimal import Decimal

from django.test import TestCase

from inventory.financials import inventory_financial_snapshot
from inventory.models import InventoryItem
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company


class InventoryFinancialIntegrityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Financial Integrity Co",
            slug="financial-integrity-co",
            phone="9000011001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        supplier = Supplier.objects.create(
            company=self.company,
            name="Financial Supplier",
        )
        category = PartCategory.objects.create(name="Financial Parts")
        part = PartMaster.objects.create(
            name="Financial Filter",
            code="FIN-FILTER",
            category=category,
            is_serialized=True,
        )
        purchase = Purchase.objects.create(
            company=self.company,
            supplier=supplier,
            invoice_number="FIN-001",
            invoice_date=date(2026, 9, 29),
        )
        self.purchase_item = PurchaseItem.objects.create(
            company=self.company,
            purchase=purchase,
            part=part,
            quantity=5,
            purchase_price=Decimal("125.50"),
        )

    def _stock(self, status, suffix):
        return InventoryItem.objects.create(
            company=self.company,
            purchase_item=self.purchase_item,
            part=self.purchase_item.part,
            serial_number=f"FIN-{suffix}",
            barcode=f"FIN-{suffix}",
            status=status,
        )

    def test_snapshot_uses_quantity_weighted_purchase_value_and_state_values(self):
        self._stock("PENDING_RECEIPT", "PENDING")
        self._stock("IN_STOCK", "STOCK")
        self._stock("ISSUED", "ISSUED")
        self._stock("INSTALLED", "INSTALLED")
        self._stock("RETURNED", "RETURNED")

        snapshot = inventory_financial_snapshot(self.company.id)

        self.assertEqual(snapshot["purchased_units"], 5)
        self.assertEqual(snapshot["physical_units"], 5)
        self.assertEqual(snapshot["unit_gap"], 0)
        self.assertEqual(snapshot["purchased_value"], Decimal("627.50"))
        self.assertEqual(snapshot["received_units"], 4)
        self.assertEqual(snapshot["received_value"], Decimal("502.00"))
        self.assertEqual(snapshot["warehouse_units"], 2)
        self.assertEqual(snapshot["warehouse_stock_value"], Decimal("251.00"))
        self.assertEqual(snapshot["issued"], 1)
        self.assertEqual(snapshot["issued_value"], Decimal("125.50"))
        self.assertEqual(snapshot["installed"], 1)
        self.assertEqual(snapshot["installed_value"], Decimal("125.50"))
        self.assertEqual(snapshot["returned"], 1)

    def test_snapshot_exposes_missing_physical_units_instead_of_hiding_gap(self):
        self._stock("IN_STOCK", "ONLY-ONE")

        snapshot = inventory_financial_snapshot(self.company.id)

        self.assertEqual(snapshot["purchased_units"], 5)
        self.assertEqual(snapshot["physical_units"], 1)
        self.assertEqual(snapshot["unit_gap"], 4)
        self.assertEqual(snapshot["purchased_value"], Decimal("627.50"))
        self.assertEqual(snapshot["warehouse_stock_value"], Decimal("125.50"))
