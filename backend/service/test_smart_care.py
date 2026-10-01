from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assets.models import ROAsset
from customers.models import Customer
from employees.models import EmployeeProfile
from installation.models import Installation, InstallationPart
from partmaster.models import PartCategory, PartMaster
from products.models import ProductCategory, ROModel
from tenancy.models import Company

from .models import PartServiceCycleAudit, Service, ServiceIntervalPolicy, ServicePart
from .smart_care import (
    HEALTHY,
    NOT_CONFIGURED,
    cycle_start_for_part,
    part_health,
    record_replacement_cycle,
    reminder_schedule,
)


class SmartCareTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(
            name="Smart Care Test Company",
            slug="smart-care-test",
            phone="9000099001",
        )
        self.engineer_user = User.objects.create_user(
            phone="9333399001",
            password="TestPassword123!",
            role="ENGINEER",
        )
        self.engineer = EmployeeProfile.objects.create(
            company=self.company,
            user=self.engineer_user,
            employee_id="CARE-ENG-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        product_category = ProductCategory.objects.create(name="Smart Care Category")
        self.ro_model = ROModel.objects.create(
            category=product_category,
            model_name="Smart Care RO",
            capacity="12 LPH",
            business_type="RENT",
            monthly_rent=Decimal("900.00"),
            installation_charge=Decimal("600.00"),
            security_deposit=Decimal("0.00"),
            selling_price=Decimal("10000.00"),
            warranty_months=12,
        )
        self.customer = Customer.objects.create(
            company=self.company,
            name="Smart Care Customer",
            phone="8333399001",
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model=self.ro_model.model_name,
        )
        self.asset = ROAsset.objects.create(
            ro_model=self.ro_model,
            serial_number="CARE-ASSET-001",
            status="INSTALLED",
            current_customer=self.customer,
        )
        category = PartCategory.objects.create(name="Smart Care Filters")
        self.part = PartMaster.objects.create(
            name="Sediment Filter",
            code="CARE-SED-001",
            category=category,
        )
        self.installed_at = timezone.now() - timedelta(days=10)
        self.installation = Installation.objects.create(
            customer=self.customer,
            ro_asset=self.asset,
            engineer=self.engineer,
            scheduled_date=self.installed_at,
            completed_date=self.installed_at,
            status="COMPLETED",
        )
        InstallationPart.objects.create(
            installation=self.installation,
            part=self.part,
            quantity=1,
        )

    def _policy(self, interval_days=100, reminders=None):
        return ServiceIntervalPolicy.objects.create(
            company=self.company,
            part=self.part,
            ro_model=self.ro_model,
            interval_days=interval_days,
            due_soon_days=20,
            reminder_days=reminders if reminders is not None else [30, 15, 7, 1, 0],
        )

    def _completed_service(self, completed_at):
        service = Service.objects.create(
            company=self.company,
            customer=self.customer,
            engineer=self.engineer,
            ro_asset=self.asset,
            service_type="REGULAR",
            scheduled_date=completed_at,
            status="PENDING",
        )
        Service.objects.filter(pk=service.pk).update(
            status="COMPLETED",
            completed_date=completed_at,
        )
        service.refresh_from_db()
        return service

    def test_no_universal_due_date_without_configured_policy(self):
        health = part_health(self.company, self.asset, self.part)
        self.assertEqual(health["health_status"], NOT_CONFIGURED)
        self.assertIsNone(health["expected_service_interval_days"])
        self.assertIsNone(health["next_due_date"])

    def test_configured_interval_calculates_due_date(self):
        self._policy(interval_days=100)
        today = self.installed_at.date() + timedelta(days=10)
        health = part_health(self.company, self.asset, self.part, today=today)
        self.assertEqual(health["health_status"], HEALTHY)
        self.assertEqual(
            health["next_due_date"],
            self.installed_at.date() + timedelta(days=100),
        )
        self.assertEqual(health["days_remaining"], 90)

    def test_reminder_schedule_uses_configured_offsets(self):
        policy = self._policy(interval_days=100, reminders=[30, 7, 7, 0, -1, "bad"])
        due = self.installed_at.date() + timedelta(days=100)
        schedule = reminder_schedule(policy, due)
        self.assertEqual([item["days_before_due"] for item in schedule], [30, 7, 0])
        self.assertEqual(schedule[0]["remind_on"], due - timedelta(days=30))

    def test_cleaning_does_not_reset_cycle(self):
        self._policy()
        service = self._completed_service(timezone.now())
        cleaned = ServicePart.objects.create(
            service=service,
            part=self.part,
            action=ServicePart.ACTION_CLEANED,
        )
        self.assertIsNone(record_replacement_cycle(cleaned))
        cycle_start, source, _ = cycle_start_for_part(self.asset, self.part)
        self.assertEqual(source, "INSTALLATION")
        self.assertEqual(cycle_start, self.installed_at)

    def test_replacement_resets_only_cycle_and_preserves_history(self):
        self._policy(interval_days=100)
        replaced_at = timezone.now()
        service = self._completed_service(replaced_at)
        replacement = ServicePart.objects.create(
            service=service,
            part=self.part,
            action=ServicePart.ACTION_REPLACED,
            verification_method="CUSTOMER_OTP",
        )

        audit = record_replacement_cycle(replacement)
        self.assertIsNotNone(audit)
        self.assertEqual(audit.old_due_date, self.installed_at.date() + timedelta(days=100))
        self.assertEqual(audit.new_due_date, replaced_at.date() + timedelta(days=100))
        self.assertTrue(InstallationPart.objects.filter(pk__isnull=False, part=self.part).exists())
        self.assertTrue(ServicePart.objects.filter(pk=replacement.pk).exists())

        cycle_start, source, source_row = cycle_start_for_part(self.asset, self.part)
        self.assertEqual(source, "REPLACEMENT")
        self.assertEqual(source_row.pk, replacement.pk)
        self.assertEqual(cycle_start, replaced_at)

    def test_replacement_cycle_retry_is_idempotent(self):
        self._policy()
        service = self._completed_service(timezone.now())
        replacement = ServicePart.objects.create(
            service=service,
            part=self.part,
            action=ServicePart.ACTION_REPLACED,
            verification_method="CUSTOMER_OTP",
        )
        first = record_replacement_cycle(replacement)
        second = record_replacement_cycle(replacement)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            PartServiceCycleAudit.objects.filter(source_service_part=replacement).count(),
            1,
        )

    def test_cycle_audit_is_immutable(self):
        self._policy()
        service = self._completed_service(timezone.now())
        replacement = ServicePart.objects.create(
            service=service,
            part=self.part,
            action=ServicePart.ACTION_REPLACED,
        )
        audit = record_replacement_cycle(replacement)
        audit.verification_method = "CHANGED"
        with self.assertRaises(ValueError):
            audit.save()
        with self.assertRaises(ValueError):
            audit.delete()
