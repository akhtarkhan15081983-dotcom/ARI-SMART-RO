from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import threading

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from django.utils import timezone

from assets.models.asset import ROAsset
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.models import Job
from products.models import ProductCategory, ROModel
from service.models import Service


class HumanReadableIdConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        User = get_user_model()
        user = User.objects.create_user(
            phone="9555500101",
            password="Strong@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer = EmployeeProfile.objects.create(
            user=user,
            employee_id="ID-RACE-ENG",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
            salary=Decimal("20000"),
        )
        self.customer = Customer.objects.create(
            name="ID Race Base Customer",
            phone="9555500102",
            address="Race Address",
            city="Moradabad",
            state="Uttar Pradesh",
            pincode="244001",
            ro_model="ARI TEST",
            assigned_engineer=self.engineer,
        )
        category = ProductCategory.objects.create(name="ID Race RO")
        ro_model = ROModel.objects.create(
            category=category,
            model_name="ID Race Model",
            capacity="12 LPH",
            business_type="RENT",
        )
        self.asset = ROAsset.objects.create(
            ro_model=ro_model,
            serial_number="ID-RACE-ASSET-1",
        )

    def _parallel(self, factory):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency allocator proof requires PostgreSQL advisory locks.")
        barrier = threading.Barrier(2)

        def run(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return factory(index)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, index) for index in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_customer_ids_and_card_numbers_are_unique_under_concurrent_create(self):
        rows = self._parallel(
            lambda index: Customer.objects.create(
                name=f"Concurrent Customer {index}",
                phone=f"95555002{index:02d}",
                address="Race Address",
                city="Moradabad",
                state="Uttar Pradesh",
                pincode="244001",
                ro_model="ARI TEST",
            )
        )
        ids = [row.customer_id for row in rows]
        cards = [row.card_number for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(cards), len(set(cards)))
        self.assertTrue(all(value.startswith(f"CUS-{timezone.now().year}-") for value in ids))
        self.assertTrue(all(value.startswith(f"ARI-{timezone.now().year}-") for value in cards))

    def test_job_ids_are_unique_under_concurrent_create(self):
        rows = self._parallel(
            lambda _index: Job.objects.create(
                customer=self.customer,
                engineer=self.engineer,
                job_type="SERVICE",
                scheduled_date=timezone.now(),
            )
        )
        ids = [row.job_id for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(value.startswith(f"JOB-{timezone.now().year}-") for value in ids))

    def test_service_ids_are_unique_under_concurrent_create(self):
        rows = self._parallel(
            lambda _index: Service.objects.create(
                customer=self.customer,
                engineer=self.engineer,
                ro_asset=self.asset,
                scheduled_date=timezone.now(),
            )
        )
        ids = [row.service_id for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(value.startswith(f"SER-{timezone.now().year}-") for value in ids))

    def test_complaint_ids_are_unique_under_concurrent_create(self):
        rows = self._parallel(
            lambda index: Complaint.objects.create(
                customer=self.customer,
                engineer=self.engineer,
                complaint_type="OTHER",
                description=f"Concurrent complaint {index}",
            )
        )
        ids = [row.complaint_id for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(value.startswith(f"CMP-{timezone.now().year}-") for value in ids))
