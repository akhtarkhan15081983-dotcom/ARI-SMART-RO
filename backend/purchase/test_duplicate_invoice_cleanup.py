import io
import json
from datetime import date
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from inventory.models import InventoryItem
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company


class DuplicateInvoiceShellCleanupTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="Cleanup Tenant",
            slug="cleanup-tenant",
            phone="9000099999",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.supplier = Supplier.objects.create(company=self.company, name="Cleanup Supplier")
        category = PartCategory.objects.create(name="Cleanup Parts")
        self.part = PartMaster.objects.create(
            name="Cleanup Part",
            code="CLEAN-001",
            category=category,
        )

    def _purchase(self):
        purchase = Purchase.objects.create(
            company=self.company,
            supplier=self.supplier,
            invoice_number="INV CLEAN 001",
            invoice_date=date(2026, 9, 29),
            entry_source="MANUAL",
        )
        item = PurchaseItem.objects.create(
            company=self.company,
            purchase=purchase,
            part=self.part,
            quantity=5,
            purchase_price="125.00",
        )
        return purchase, item

    def _fixture(self):
        shell_one, _ = self._purchase()
        shell_two, _ = self._purchase()
        canonical, canonical_item = self._purchase()
        inventory = InventoryItem.objects.create(
            company=self.company,
            purchase_item=canonical_item,
            part=self.part,
            status="ISSUED",
        )
        return shell_one, shell_two, canonical, inventory

    def test_dry_run_identifies_only_zero_inventory_shells_without_writes(self):
        shell_one, shell_two, canonical, inventory = self._fixture()
        before_purchase_ids = list(Purchase.objects.order_by("id").values_list("id", flat=True))
        output = io.StringIO()

        with patch(
            "purchase.management.commands.cleanup_duplicate_supplier_invoice_shells._current_database_name",
            return_value="ari_rehearsal_test",
        ):
            call_command("cleanup_duplicate_supplier_invoice_shells", stdout=output)

        report = json.loads(output.getvalue())
        after_purchase_ids = list(Purchase.objects.order_by("id").values_list("id", flat=True))

        self.assertEqual(after_purchase_ids, before_purchase_ids)
        self.assertEqual(report["mode"], "DRY_RUN_ONLY")
        self.assertFalse(report["writes_performed"])
        self.assertEqual(report["safe_candidate_group_count"], 1)
        self.assertEqual(report["safe_shell_purchase_count"], 2)
        self.assertEqual(report["blocked_group_count"], 0)
        self.assertEqual(report["candidates"][0]["canonical_purchase_id"], canonical.id)
        self.assertEqual(
            report["candidates"][0]["shell_purchase_ids"],
            [shell_one.id, shell_two.id],
        )
        self.assertTrue(InventoryItem.objects.filter(pk=inventory.pk).exists())

    def test_apply_deletes_only_shells_and_preserves_canonical_inventory(self):
        shell_one, shell_two, canonical, inventory = self._fixture()
        output = io.StringIO()

        with patch(
            "purchase.management.commands.cleanup_duplicate_supplier_invoice_shells._current_database_name",
            return_value="ari_rehearsal_test",
        ):
            call_command(
                "cleanup_duplicate_supplier_invoice_shells",
                apply=True,
                confirm_rehearsal_db=True,
                expected_database_name="ari_rehearsal_test",
                stdout=output,
            )

        report = json.loads(output.getvalue())
        self.assertEqual(report["mode"], "APPLY")
        self.assertTrue(report["writes_performed"])
        self.assertEqual(report["deleted_purchase_count"], 2)
        self.assertEqual(report["deleted_purchase_item_count"], 2)
        self.assertFalse(Purchase.objects.filter(pk=shell_one.pk).exists())
        self.assertFalse(Purchase.objects.filter(pk=shell_two.pk).exists())
        self.assertTrue(Purchase.objects.filter(pk=canonical.pk).exists())
        self.assertTrue(InventoryItem.objects.filter(pk=inventory.pk).exists())

    def test_apply_refuses_production_database(self):
        self._fixture()
        before_count = Purchase.objects.count()

        with patch(
            "purchase.management.commands.cleanup_duplicate_supplier_invoice_shells._current_database_name",
            return_value="ari_smart_ro",
        ):
            with self.assertRaises(CommandError):
                call_command(
                    "cleanup_duplicate_supplier_invoice_shells",
                    apply=True,
                    confirm_rehearsal_db=True,
                    expected_database_name="ari_smart_ro",
                    stdout=io.StringIO(),
                )

        self.assertEqual(Purchase.objects.count(), before_count)
