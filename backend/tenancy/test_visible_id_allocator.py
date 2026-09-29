from concurrent.futures import ThreadPoolExecutor
from datetime import date

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from assets.models import ROAsset
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.models import Job
from products.models import ProductCategory, ROModel
from service.models import Service


class VisibleIdAllocatorConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        User = get_user_model()
        engineer_user = User.objects.create_user(
            phone="9899000001",
            password="Allocator@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            user=engineer_user,
            employee_id="ALLOC-ENG-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.base_customer = Customer.objects.create(
            name="Allocator Base Customer",
            phone="9899000002",
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

    def _thread(self, creator, index):
        close_old_connections()
        try:
            return creator(index)
        finally:
            close_old_connections()

    def _run_concurrent(self, creator, count=16):
        with ThreadPoolExecutor(max_workers=8) as executor:
            return list(executor.map(lambda index: self._thread(creator, index), range(count)))

    def _create_customer(self, index):
        row = Customer.objects.create(
            name=f"Concurrent Customer {index}",
            phone=f"98{index:08d}"[-10:],
            address="Allocator test",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
        )
        return row.customer_id, row.card_number

    def _create_job(self, index):
        row = Job.objects.create(
            customer_id=self.base_customer.id,
            engineer_id=self.engineer.id,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
            remarks=f"Concurrent job {index}",
        )
        return row.job_id

    def _create_service(self, index):
        row = Service.objects.create(
            customer_id=self.base_customer.id,
            engineer_id=self.engineer.id,
            ro_asset_id=self.asset.id,
            service_type="REGULAR",
            scheduled_date=timezone.now(),
            remarks=f"Concurrent service {index}",
        )
        return row.service_id

    def _create_complaint(self, index):
        row = Complaint.objects.create(
            customer_id=self.base_customer.id,
            complaint_type="OTHER",
            description=f"Concurrent complaint {index}",
        )
        return row.complaint_id

    def test_simultaneous_customer_creates_never_duplicate_visible_ids(self):
        results = self._run_concurrent(self._create_customer)
        ids = [customer_id for customer_id, _ in results]
        cards = [card for _, card in results]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(cards), len(set(cards)))
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"CUS-{year}-") for value in ids))
        self.assertTrue(all(value.startswith(f"ARI-{year}-") for value in cards))

    def test_simultaneous_job_creates_never_duplicate_visible_ids(self):
        ids = self._run_concurrent(self._create_job)
        self.assertEqual(len(ids), len(set(ids)))
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"JOB-{year}-") for value in ids))

    def test_simultaneous_service_creates_never_duplicate_visible_ids(self):
        ids = self._run_concurrent(self._create_service)
        self.assertEqual(len(ids), len(set(ids)))
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"SER-{year}-") for value in ids))

    def test_simultaneous_complaint_creates_never_duplicate_visible_ids(self):
        ids = self._run_concurrent(self._create_complaint)
        self.assertEqual(len(ids), len(set(ids)))
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"CMP-{year}-") for value in ids))

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
