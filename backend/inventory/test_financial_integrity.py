from datetime import date
from decimal import Decimal
from io import BytesIO

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.financials import inventory_financial_snapshot
from inventory.models import InventoryItem
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company, CompanyMembership


class InventoryFinancialIntegrityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(
            name="Financial Integrity Co",
            slug="financial-integrity-co",
            phone="9000011001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.other_company = Company.objects.create(
            name="Other Financial Co",
            slug="other-financial-co",
            phone="9000011002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9899200001",
            password="Financial@123",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="ADMIN",
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

        self.supplier = Supplier.objects.create(
            company=self.company,
            name="Financial Supplier",
        )
        category = PartCategory.objects.create(name="Financial Parts")
        self.part = PartMaster.objects.create(
            name="Financial Filter",
            code="FIN-FILTER",
            category=category,
            is_serialized=True,
        )
        self.non_serialized_part = PartMaster.objects.create(
            name="Financial Non Serialized",
            code="FIN-NONSERIAL",
            category=category,
            is_serialized=False,
        )
        purchase = Purchase.objects.create(
            company=self.company,
            supplier=self.supplier,
            invoice_number="FIN-001",
            invoice_date=date(2026, 9, 29),
        )
        self.purchase_item = PurchaseItem.objects.create(
            company=self.company,
            purchase=purchase,
            part=self.part,
            quantity=5,
            purchase_price=Decimal("125.50"),
        )

    def _stock(self, status, suffix, *, purchase_item=None, company=None):
        purchase_item = purchase_item or self.purchase_item
        company = company or self.company
        serial = f"FIN-{suffix}" if purchase_item.part.is_serialized else None
        return InventoryItem.objects.create(
            company=company,
            purchase_item=purchase_item,
            part=purchase_item.part,
            serial_number=serial,
            barcode=serial or "",
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
        # Installed units are not available warehouse stock; returned units are.
        self.assertEqual(snapshot["warehouse_stock_value"], Decimal("251.00"))
        self.assertEqual(
            snapshot["purchased_value"]
            - (
                Decimal("125.50")  # pending receipt
                + snapshot["warehouse_stock_value"]
                + snapshot["issued_value"]
                + snapshot["installed_value"]
                + snapshot["scrap_value"]
            ),
            Decimal("0.00"),
        )

    def test_snapshot_exposes_missing_physical_units_instead_of_hiding_gap(self):
        self._stock("IN_STOCK", "ONLY-ONE")

        snapshot = inventory_financial_snapshot(self.company.id)

        self.assertEqual(snapshot["purchased_units"], 5)
        self.assertEqual(snapshot["physical_units"], 1)
        self.assertEqual(snapshot["unit_gap"], 4)
        self.assertEqual(snapshot["purchased_value"], Decimal("627.50"))
        self.assertEqual(snapshot["warehouse_stock_value"], Decimal("125.50"))

    def test_non_serialized_and_zero_price_inventory_reconcile_exactly(self):
        purchase = Purchase.objects.create(
            company=self.company,
            supplier=self.supplier,
            invoice_number="FIN-ZERO-001",
            invoice_date=date(2026, 9, 29),
        )
        zero_item = PurchaseItem.objects.create(
            company=self.company,
            purchase=purchase,
            part=self.non_serialized_part,
            quantity=2,
            purchase_price=Decimal("0.00"),
        )
        self._stock("IN_STOCK", "NS-1", purchase_item=zero_item)
        self._stock("RETURNED", "NS-2", purchase_item=zero_item)

        snapshot = inventory_financial_snapshot(self.company.id)

        self.assertEqual(snapshot["purchased_units"], 7)
        self.assertEqual(snapshot["physical_units"], 2)
        self.assertEqual(snapshot["unit_gap"], 5)
        self.assertEqual(snapshot["purchased_value"], Decimal("627.50"))
        self.assertEqual(snapshot["warehouse_units"], 2)
        self.assertEqual(snapshot["warehouse_stock_value"], Decimal("0.00"))

    def test_snapshot_excludes_other_tenant_stock_and_value(self):
        other_supplier = Supplier.objects.create(
            company=self.other_company,
            name="Other Supplier",
        )
        other_purchase = Purchase.objects.create(
            company=self.other_company,
            supplier=other_supplier,
            invoice_number="OTHER-001",
            invoice_date=date(2026, 9, 29),
        )
        other_item = PurchaseItem.objects.create(
            company=self.other_company,
            purchase=other_purchase,
            part=self.part,
            quantity=3,
            purchase_price=Decimal("999.99"),
        )
        for index in range(3):
            self._stock(
                "IN_STOCK",
                f"OTHER-{index}",
                purchase_item=other_item,
                company=self.other_company,
            )
        self._stock("IN_STOCK", "OWN")

        snapshot = inventory_financial_snapshot(self.company.id)

        self.assertEqual(snapshot["purchased_units"], 5)
        self.assertEqual(snapshot["purchased_value"], Decimal("627.50"))
        self.assertEqual(snapshot["physical_units"], 1)
        self.assertEqual(snapshot["warehouse_stock_value"], Decimal("125.50"))

    def test_summary_excel_and_database_financial_totals_match_exactly(self):
        for status, suffix in (
            ("PENDING_RECEIPT", "PENDING"),
            ("IN_STOCK", "STOCK"),
            ("ISSUED", "ISSUED"),
            ("INSTALLED", "INSTALLED"),
            ("RETURNED", "RETURNED"),
        ):
            self._stock(status, suffix)

        database = inventory_financial_snapshot(self.company.id)
        summary_response = self.client.get("/api/inventory/workflow/summary/")
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.data["summary"]

        report_response = self.client.get("/api/inventory/workflow/reports/inventory.xlsx")
        self.assertEqual(report_response.status_code, 200)
        workbook = openpyxl.load_workbook(BytesIO(report_response.content), data_only=True)
        sheet = workbook["Executive Summary"]
        excel = {row[0].value: row[1].value for row in sheet.iter_rows(min_row=2)}

        money_fields = (
            ("purchased_value", "Purchased Value"),
            ("received_value", "Received Value"),
            ("warehouse_stock_value", "Stock Value"),
            ("issued_value", "Issued Value"),
            ("installed_value", "Installed Value"),
            ("scrap_value", "Scrap Value"),
        )
        for field, excel_label in money_fields:
            expected = database[field]
            self.assertEqual(Decimal(str(summary[field])), expected)
            self.assertEqual(Decimal(str(excel[excel_label])), expected)

        count_fields = (
            ("purchased_units", "Purchased Units"),
            ("physical_units", "Physical Inventory Units"),
            ("unit_gap", "Purchase/Inventory Unit Gap"),
            ("received_units", "Received Units"),
            ("warehouse_units", "Warehouse Units"),
            ("pending_receipt", "Pending Receipt"),
            ("in_stock", "In Stock"),
            ("issued", "Issued"),
            ("installed", "Installed"),
            ("returned", "Returned"),
            ("scrap", "Scrap"),
        )
        for field, excel_label in count_fields:
            self.assertEqual(summary[field], database[field])
            self.assertEqual(excel[excel_label], database[field])
