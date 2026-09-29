import io
import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from employees.models import EmployeeProfile
from inventory.models import InventoryItem
from jobs.models import Job
from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, PurchaseItem, Supplier
from tenancy.models import Company, CompanyMembership


class TenantMigrationRehearsalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company_a = Company.objects.create(
            name="Rehearsal A",
            slug="rehearsal-a",
            phone="9000013001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Rehearsal B",
            slug="rehearsal-b",
            phone="9000013002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        user_a = User.objects.create_user(
            phone="9555513001",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        user_b = User.objects.create_user(
            phone="9555513002",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.verifier = User.objects.create_user(
            phone="9555513003",
            password="Strong@123",
            role="OFFICE",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.verifier,
            role="STAFF",
            is_active=True,
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=user_a,
            employee_id="REHEARSE-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("20000"),
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=user_b,
            employee_id="REHEARSE-B",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("20000"),
        )
        self.legacy_customer = Customer.objects.create(
            name="Resolvable Legacy Customer",
            phone="9555513101",
            address="Legacy Address",
            city="Moradabad",
            state="Uttar Pradesh",
            pincode="244001",
            ro_model="ARI TEST",
            assigned_engineer=self.engineer_a,
        )
        self.owned_customer = Customer.objects.create(
            company=self.company_a,
            name="Owned Customer",
            phone="9555513102",
            address="Owned Address",
            city="Moradabad",
            state="Uttar Pradesh",
            pincode="244001",
            ro_model="ARI TEST",
            assigned_engineer=self.engineer_a,
        )
        self.mismatched_job = Job.objects.create(
            company=self.company_a,
            customer=self.owned_customer,
            engineer=self.engineer_b,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
        )

        supplier = Supplier.objects.create(name="Legacy Supplier")
        purchase = Purchase.objects.create(
            supplier=supplier,
            invoice_number="REHEARSE-INV",
            invoice_date=date(2026, 9, 29),
            verified_by=self.verifier,
        )
        category = PartCategory.objects.create(name="Rehearsal Parts")
        part = PartMaster.objects.create(
            name="Rehearsal Filter",
            code="REHEARSE-FILTER",
            category=category,
            is_serialized=True,
        )
        purchase_item = PurchaseItem.objects.create(
            purchase=purchase,
            part=part,
            quantity=1,
            purchase_price=Decimal("100.00"),
        )
        self.legacy_inventory = InventoryItem.objects.create(
            purchase_item=purchase_item,
            part=part,
            serial_number="REHEARSE-STOCK-1",
            status="PENDING_RECEIPT",
        )
        self.legacy_supplier = supplier
        self.legacy_purchase = purchase
        self.legacy_purchase_item = purchase_item

    def test_rehearsal_reports_before_projected_after_and_never_writes(self):
        output = io.StringIO()

        call_command("rehearse_tenant_migration", stdout=output)

        report = json.loads(output.getvalue())
        self.assertEqual(report["mode"], "DRY_RUN_ONLY")
        self.assertFalse(report["writes_performed"])
        self.assertIn("operational", report["before_counts"])
        self.assertIn("warehouse", report["before_counts"])
        self.assertIn("operational", report["projected_after_counts"])
        self.assertIn("warehouse", report["projected_after_counts"])
        self.assertGreaterEqual(
            report["projected_after_counts"]["operational"]["Customer"]["resolved_by_rehearsal"],
            1,
        )
        self.assertGreaterEqual(
            report["projected_after_counts"]["warehouse"]["Supplier"]["resolved_by_rehearsal"],
            1,
        )
        self.assertGreaterEqual(report["relation_inconsistency_count"], 1)
        self.assertTrue(
            any(
                row["model"] == "Job" and row["relationship"] == "engineer"
                for row in report["relation_inconsistencies"]
            )
        )

        self.legacy_customer.refresh_from_db()
        self.legacy_supplier.refresh_from_db()
        self.legacy_purchase.refresh_from_db()
        self.legacy_purchase_item.refresh_from_db()
        self.legacy_inventory.refresh_from_db()
        self.assertIsNone(self.legacy_customer.company_id)
        self.assertIsNone(self.legacy_supplier.company_id)
        self.assertIsNone(self.legacy_purchase.company_id)
        self.assertIsNone(self.legacy_purchase_item.company_id)
        self.assertIsNone(self.legacy_inventory.company_id)
