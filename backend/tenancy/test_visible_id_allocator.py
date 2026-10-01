from concurrent.futures import ThreadPoolExecutor
from datetime import date

from django.contrib.auth import get_user_model
from django.db import close_old_connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from assets.models import ROAsset
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.models import Job
from products.models import ProductCategory, ROModel
from service.models import Service
from tenancy.models import Company


class VisibleIdAllocatorConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    CONCURRENT_CREATE_COUNT = 20

    def setUp(self):
        User = get_user_model()
        self.company_a = Company.objects.create(
            name="Allocator Tenant A",
            slug="allocator-tenant-a",
            phone="9000011001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Allocator Tenant B",
            slug="allocator-tenant-b",
            phone="9000011002",
            is_active=True,
            lifecycle_status="ACTIVE",
        )

        engineer_user_a = User.objects.create_user(
            phone="9899000001",
            password="Allocator@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        engineer_user_b = User.objects.create_user(
            phone="9899000003",
            password="Allocator@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=engineer_user_a,
            employee_id="ALLOC-ENG-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=engineer_user_b,
            employee_id="ALLOC-ENG-002",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.base_customer_a = Customer.objects.create(
            company=self.company_a,
            name="Allocator Base Customer A",
            phone="9899000002",
            address="Allocator test",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )
        self.base_customer_b = Customer.objects.create(
            company=self.company_b,
            name="Allocator Base Customer B",
            phone="9899000004",
            address="Allocator test",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )
        category = ProductCategory.objects.create(name="Allocator Models")
        ro_model = ROModel.objects.create(
            category=category,
            model_name="Allocator RO",
            capacity="12 LPH",
            business_type="RENT",
        )
        self.asset = ROAsset.objects.create(
            ro_model=ro_model,
            serial_number="ALLOC-ASSET-001",
        )

    def _company_context(self, index):
        if index % 2 == 0:
            return self.company_a, self.base_customer_a, self.engineer_a
        return self.company_b, self.base_customer_b, self.engineer_b

    def _thread(self, creator, index):
        close_old_connections()
        try:
            return creator(index)
        finally:
            close_old_connections()

    def _run_concurrent(self, creator, count=None):
        count = count or self.CONCURRENT_CREATE_COUNT
        with ThreadPoolExecutor(max_workers=count) as executor:
            return list(executor.map(lambda index: self._thread(creator, index), range(count)))

    def _create_customer(self, index):
        company, _, _ = self._company_context(index)
        row = Customer.objects.create(
            company=company,
            name=f"Concurrent Customer {index}",
            phone=f"98{index:08d}"[-10:],
            address="Allocator test",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )
        return row.customer_id, row.card_number, row.company_id

    def _create_job(self, index):
        company, customer, engineer = self._company_context(index)
        row = Job.objects.create(
            company=company,
            customer_id=customer.id,
            engineer_id=engineer.id,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
            remarks=f"Concurrent job {index}",
        )
        return row.job_id, row.company_id

    def _create_service(self, index):
        company, customer, engineer = self._company_context(index)
        row = Service.objects.create(
            company=company,
            customer_id=customer.id,
            engineer_id=engineer.id,
            ro_asset_id=self.asset.id,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            remarks=f"Concurrent service {index}",
        )
        return row.service_id, row.company_id

    def _create_complaint(self, index):
        company, customer, _ = self._company_context(index)
        row = Complaint.objects.create(
            company=company,
            customer_id=customer.id,
            complaint_type="OTHER",
            description=f"Concurrent complaint {index}",
        )
        return row.complaint_id, row.company_id

    def _assert_company_mix_preserved(self, company_ids):
        expected = {
            self.company_a.id: self.CONCURRENT_CREATE_COUNT // 2,
            self.company_b.id: self.CONCURRENT_CREATE_COUNT // 2,
        }
        observed = {
            self.company_a.id: company_ids.count(self.company_a.id),
            self.company_b.id: company_ids.count(self.company_b.id),
        }
        self.assertEqual(observed, expected)

    def test_twenty_simultaneous_customer_creates_never_duplicate_visible_ids(self):
        results = self._run_concurrent(self._create_customer)
        ids = [customer_id for customer_id, _, _ in results]
        cards = [card for _, card, _ in results]
        company_ids = [company_id for _, _, company_id in results]
        self.assertEqual(len(ids), self.CONCURRENT_CREATE_COUNT)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(cards), len(set(cards)))
        self._assert_company_mix_preserved(company_ids)
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"CUS-{year}-") for value in ids))
        self.assertTrue(all(value.startswith(f"ARI-{year}-") for value in cards))

    def test_twenty_simultaneous_job_creates_never_duplicate_visible_ids(self):
        results = self._run_concurrent(self._create_job)
        ids = [visible_id for visible_id, _ in results]
        company_ids = [company_id for _, company_id in results]
        self.assertEqual(len(ids), self.CONCURRENT_CREATE_COUNT)
        self.assertEqual(len(ids), len(set(ids)))
        self._assert_company_mix_preserved(company_ids)
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"JOB-{year}-") for value in ids))

    def test_twenty_simultaneous_service_creates_never_duplicate_visible_ids(self):
        results = self._run_concurrent(self._create_service)
        ids = [visible_id for visible_id, _ in results]
        company_ids = [company_id for _, company_id in results]
        self.assertEqual(len(ids), self.CONCURRENT_CREATE_COUNT)
        self.assertEqual(len(ids), len(set(ids)))
        self._assert_company_mix_preserved(company_ids)
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"SER-{year}-") for value in ids))

    def test_twenty_simultaneous_complaint_creates_never_duplicate_visible_ids(self):
        results = self._run_concurrent(self._create_complaint)
        ids = [visible_id for visible_id, _ in results]
        company_ids = [company_id for _, company_id in results]
        self.assertEqual(len(ids), self.CONCURRENT_CREATE_COUNT)
        self.assertEqual(len(ids), len(set(ids)))
        self._assert_company_mix_preserved(company_ids)
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"CMP-{year}-") for value in ids))

    def _assert_rollback_reuses_only_uncommitted_number(
        self,
        *,
        creator,
        extractor,
        model,
        field_name,
        first_index,
        second_index,
    ):
        doomed_visible = None
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                doomed_result = creator(first_index)
                doomed_visible = extractor(doomed_result)
                raise RuntimeError("force allocator transaction rollback")

        self.assertIsNotNone(doomed_visible)
        self.assertFalse(model.objects.filter(**{field_name: doomed_visible}).exists())

        replacement_result = creator(second_index)
        replacement_visible = extractor(replacement_result)
        self.assertEqual(replacement_visible, doomed_visible)
        self.assertEqual(model.objects.filter(**{field_name: replacement_visible}).count(), 1)

    def test_allocator_rollback_is_safe_for_all_core_visible_ids(self):
        cases = (
            (
                "customer",
                self._create_customer,
                lambda result: result[0],
                Customer,
                "customer_id",
                9000,
                9001,
            ),
            (
                "job",
                self._create_job,
                lambda result: result[0],
                Job,
                "job_id",
                9002,
                9003,
            ),
            (
                "service",
                self._create_service,
                lambda result: result[0],
                Service,
                "service_id",
                9004,
                9005,
            ),
            (
                "complaint",
                self._create_complaint,
                lambda result: result[0],
                Complaint,
                "complaint_id",
                9006,
                9007,
            ),
        )
        for name, creator, extractor, model, field_name, first_index, second_index in cases:
            with self.subTest(model=name):
                self._assert_rollback_reuses_only_uncommitted_number(
                    creator=creator,
                    extractor=extractor,
                    model=model,
                    field_name=field_name,
                    first_index=first_index,
                    second_index=second_index,
                )

    def test_allocator_starts_above_legacy_high_water_mark(self):
        year = timezone.now().year
        Customer.objects.create(
            customer_id=f"CUS-{year}-009999",
            card_number=f"ARI-{year}-009999",
            name="Legacy High Water",
            phone="9800019999",
            address="Legacy",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )
        row = Customer.objects.create(
            name="New Customer",
            phone="9800020000",
            address="New",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )
        self.assertEqual(row.customer_id, f"CUS-{year}-010000")
        self.assertEqual(row.card_number, f"ARI-{year}-010000")
