import io
import json
from datetime import date

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from purchase.management.commands.audit_duplicate_supplier_invoices import (
    build_duplicate_invoice_report,
    duplicate_invoice_groups,
)
from purchase.models import Purchase, Supplier
from tenancy.models import Company


class DuplicateSupplierInvoiceAuditTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Invoice Audit A",
            slug="invoice-audit-a",
            phone="9000012001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Invoice Audit B",
            slug="invoice-audit-b",
            phone="9000012002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.supplier_a = Supplier.objects.create(company=self.company_a, name="Supplier A")
        self.supplier_a2 = Supplier.objects.create(company=self.company_a, name="Supplier A2")
        self.supplier_b = Supplier.objects.create(company=self.company_b, name="Supplier B")

    def _purchase(self, company, supplier, invoice):
        return Purchase.objects.create(
            company=company,
            supplier=supplier,
            invoice_number=invoice,
            invoice_date=date(2026, 9, 29),
        )

    def test_duplicate_detection_is_tenant_supplier_and_normalized_invoice_scoped(self):
        first = self._purchase(self.company_a, self.supplier_a, " INV  100 ")
        second = self._purchase(self.company_a, self.supplier_a, "inv100")
        self._purchase(self.company_a, self.supplier_a2, "INV100")
        self._purchase(self.company_b, self.supplier_b, "INV100")

        groups = duplicate_invoice_groups()

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["company_id"], self.company_a.id)
        self.assertEqual(group["supplier_id"], self.supplier_a.id)
        self.assertEqual(group["normalized_invoice_number"], "INV100")
        self.assertEqual(group["purchase_ids"], [first.id, second.id])

    def test_command_is_read_only_and_reports_exact_rehearsal_counts(self):
        first = self._purchase(self.company_a, self.supplier_a, "A B C")
        second = self._purchase(self.company_a, self.supplier_a, "abc")
        self._purchase(self.company_a, self.supplier_a2, "UNIQUE-1")
        before = list(Purchase.objects.order_by("id").values_list("id", "invoice_number"))
        output = io.StringIO()

        call_command("audit_duplicate_supplier_invoices", stdout=output)

        after = list(Purchase.objects.order_by("id").values_list("id", "invoice_number"))
        self.assertEqual(after, before)
        report = json.loads(output.getvalue())
        self.assertEqual(report["mode"], "DRY_RUN_ONLY")
        self.assertEqual(report["ownership_source"], "projected inventory tenant ownership; no database writes")
        self.assertEqual(report["total_purchase_count"], 3)
        self.assertEqual(report["unique_identity_count"], 2)
        self.assertEqual(report["duplicate_group_count"], 1)
        self.assertEqual(report["duplicate_row_count"], 2)
        self.assertEqual(report["blocking_issue_count"], 1)
        self.assertEqual(report["rehearsal_status"], "BLOCKED")
        self.assertFalse(report["constraint_ready"])
        self.assertEqual(
            report["duplicate_groups"][0]["purchase_ids"],
            [first.id, second.id],
        )
        self.assertIn("normalized invoice key", report["future_constraint_design"])

    def test_clean_rehearsal_is_machine_verifiable(self):
        self._purchase(self.company_a, self.supplier_a, "INV-001")
        self._purchase(self.company_a, self.supplier_a2, "INV-001")
        self._purchase(self.company_b, self.supplier_b, "INV-001")

        report = build_duplicate_invoice_report()

        self.assertEqual(report["duplicate_group_count"], 0)
        self.assertEqual(report["blank_identity_row_count"], 0)
        self.assertEqual(report["unresolved_company_row_count"], 0)
        self.assertEqual(report["blocking_issue_count"], 0)
        self.assertEqual(report["rehearsal_status"], "CLEAN")
        self.assertTrue(report["constraint_ready"])

        output = io.StringIO()
        call_command(
            "audit_duplicate_supplier_invoices",
            fail_on_conflict=True,
            stdout=output,
        )
        self.assertEqual(json.loads(output.getvalue())["rehearsal_status"], "CLEAN")

    def test_fail_on_conflict_blocks_duplicate_identity(self):
        self._purchase(self.company_a, self.supplier_a, "INV 200")
        self._purchase(self.company_a, self.supplier_a, "inv200")

        with self.assertRaises(CommandError):
            call_command(
                "audit_duplicate_supplier_invoices",
                fail_on_conflict=True,
                stdout=io.StringIO(),
            )

    def test_blank_identity_and_unresolved_company_are_explicit_blockers(self):
        blank = self._purchase(self.company_a, self.supplier_a, "   ")
        legacy_supplier = Supplier.objects.create(company=None, name="Legacy Supplier")
        unresolved = self._purchase(None, legacy_supplier, "LEGACY-001")

        report = build_duplicate_invoice_report()

        self.assertEqual(report["duplicate_group_count"], 0)
        self.assertEqual(report["blank_identity_purchase_ids"], [blank.id])
        self.assertEqual(report["unresolved_company_purchase_ids"], [unresolved.id])
        self.assertEqual(report["blank_identity_row_count"], 1)
        self.assertEqual(report["unresolved_company_row_count"], 1)
        self.assertEqual(report["blocking_issue_count"], 2)
        self.assertEqual(report["rehearsal_status"], "BLOCKED")
        self.assertFalse(report["constraint_ready"])

    def test_single_company_projection_resolves_legacy_purchase_without_writing(self):
        Company.objects.exclude(pk=self.company_a.pk).delete()
        self.supplier_b.delete()
        self.supplier_a2.delete()
        self.supplier_a.company = None
        self.supplier_a.save(update_fields=["company"])

        legacy = self._purchase(None, self.supplier_a, "LEGACY-ONLY-001")
        before_company_id = legacy.company_id

        report = build_duplicate_invoice_report()

        legacy.refresh_from_db()
        self.assertIsNone(before_company_id)
        self.assertIsNone(legacy.company_id)
        self.assertEqual(report["unresolved_company_row_count"], 0)
        self.assertEqual(report["blocking_issue_count"], 0)
        self.assertEqual(report["rehearsal_status"], "CLEAN")
        self.assertTrue(report["constraint_ready"])
