import io
import json
from datetime import date

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.models import Job
from tenancy.models import Company
from tenancy.tenant_backfill import build_ownership_plan


class TenantOwnershipBackfillTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(
            name="Tenant A",
            slug="tenant-backfill-a",
            phone="9000000001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Tenant B",
            slug="tenant-backfill-b",
            phone="9000000002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        user_a = User.objects.create_user(
            phone="9111111111", password="Strong@123", role="ENGINEER", is_active=True
        )
        user_b = User.objects.create_user(
            phone="9222222222", password="Strong@123", role="ENGINEER", is_active=True
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=user_a,
            employee_id="BACKFILL-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=user_b,
            employee_id="BACKFILL-B",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.safe = self._customer("Safe Customer", "9300000001", self.engineer_a)
        self.unresolved = self._customer("Unresolved Customer", "9300000002", None)
        self.conflict = self._customer("Conflict Customer", "9300000003", self.engineer_a)
        Job.objects.create(
            customer=self.conflict,
            engineer=self.engineer_b,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
        )

    def _customer(self, name, phone, engineer):
        return Customer.objects.create(
            name=name,
            phone=phone,
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
            assigned_engineer=engineer,
        )

    def _customer_decisions(self):
        return {
            decision.pk: decision
            for decision in build_ownership_plan()
            if decision.model == "Customer"
        }

    def test_plan_classifies_resolved_unresolved_and_conflict_without_phone_inference(self):
        decisions = self._customer_decisions()
        self.assertEqual(decisions[self.safe.pk].status, "RESOLVED")
        self.assertEqual(decisions[self.safe.pk].company_id, self.company_a.id)
        self.assertEqual(decisions[self.unresolved.pk].status, "UNRESOLVED")
        self.assertIsNone(decisions[self.unresolved.pk].company_id)
        self.assertEqual(decisions[self.conflict.pk].status, "CONFLICT")
        self.assertIsNone(decisions[self.conflict.pk].company_id)
        sources = {source for source, _ in decisions[self.conflict.pk].evidence}
        self.assertIn("assigned_engineer", sources)
        self.assertIn("job_engineer", sources)

    def test_command_defaults_to_dry_run_and_writes_nothing(self):
        stdout = io.StringIO()
        call_command("backfill_tenant_ownership", stdout=stdout)
        payload = json.loads(stdout.getvalue().strip().splitlines()[-1])
        self.assertEqual(payload["mode"], "DRY_RUN")
        self.assertEqual(payload["applied_count"], 0)
        self.safe.refresh_from_db()
        self.unresolved.refresh_from_db()
        self.conflict.refresh_from_db()
        self.assertIsNone(self.safe.company_id)
        self.assertIsNone(self.unresolved.company_id)
        self.assertIsNone(self.conflict.company_id)

    def test_apply_writes_only_resolved_rows_and_quarantines_conflicts(self):
        stdout = io.StringIO()
        call_command("backfill_tenant_ownership", "--apply", stdout=stdout)
        payload = json.loads(stdout.getvalue().strip().splitlines()[-1])
        self.assertEqual(payload["mode"], "APPLY")
        self.safe.refresh_from_db()
        self.unresolved.refresh_from_db()
        self.conflict.refresh_from_db()
        self.assertEqual(self.safe.company_id, self.company_a.id)
        self.assertIsNone(self.unresolved.company_id)
        self.assertIsNone(self.conflict.company_id)
        conflict_rows = [
            row for row in payload["rows"]
            if row["model"] == "Customer" and row["pk"] == self.conflict.pk
        ]
        self.assertEqual(conflict_rows[0]["status"], "CONFLICT")
