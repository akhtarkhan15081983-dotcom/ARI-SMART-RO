from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from complaints.models import Complaint
from customers.models import Customer
from jobs.models import Job
from service.models import Service

from .identifiers import allocate_operational_number
from .models import HumanReadableIdSequence
from .signals import (
    allocate_complaint_id,
    allocate_customer_id,
    allocate_job_id,
    allocate_service_id,
)


class HumanReadableIdAllocatorTests(TransactionTestCase):
    reset_sequences = True

    def _allocate(self, spec):
        close_old_connections()
        try:
            return allocate_operational_number(**spec)
        finally:
            close_old_connections()

    def test_each_operational_namespace_is_collision_safe_under_concurrency(self):
        year = timezone.now().year
        specs = (
            {
                "namespace": "CUSTOMER",
                "model_label": "customers.Customer",
                "field_name": "customer_id",
                "prefix": "CUS",
                "year": year,
            },
            {
                "namespace": "JOB",
                "model_label": "jobs.Job",
                "field_name": "job_id",
                "prefix": "JOB",
                "year": year,
            },
            {
                "namespace": "SERVICE",
                "model_label": "service.Service",
                "field_name": "service_id",
                "prefix": "SER",
                "year": year,
            },
            {
                "namespace": "COMPLAINT",
                "model_label": "complaints.Complaint",
                "field_name": "complaint_id",
                "prefix": "CMP",
                "year": year,
            },
        )
        for spec in specs:
            with ThreadPoolExecutor(max_workers=6) as pool:
                values = list(pool.map(lambda _: self._allocate(spec), range(12)))
            self.assertEqual(len(values), len(set(values)))
            self.assertEqual(sorted(values), list(range(1, 13)))
            sequence = HumanReadableIdSequence.objects.get(
                namespace=spec["namespace"], year=year
            )
            self.assertEqual(sequence.next_value, 13)

    def test_allocator_reseeds_above_late_legacy_import(self):
        year = timezone.now().year
        spec = {
            "namespace": "CUSTOMER",
            "model_label": "customers.Customer",
            "field_name": "customer_id",
            "prefix": "CUS",
            "year": year,
        }
        self.assertEqual(allocate_operational_number(**spec), 1)
        Customer.objects.create(
            customer_id=f"CUS-{year}-000125",
            card_number=f"ARI-{year}-000125",
            name="Legacy High Water",
            phone="9000000999",
            address="Legacy",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI",
        )
        self.assertEqual(allocate_operational_number(**spec), 126)

    def test_signals_preserve_visible_identifier_formats(self):
        year = timezone.now().year

        customer = Customer()
        allocate_customer_id(Customer, customer)
        self.assertRegex(customer.customer_id, rf"^CUS-{year}-\d{{6}}$")
        self.assertRegex(customer.card_number, rf"^ARI-{year}-\d{{6}}$")

        job = Job()
        allocate_job_id(Job, job)
        self.assertRegex(job.job_id, rf"^JOB-{year}-\d{{6}}$")

        service = Service()
        allocate_service_id(Service, service)
        self.assertRegex(service.service_id, rf"^SER-{year}-\d{{6}}$")

        complaint = Complaint()
        allocate_complaint_id(Complaint, complaint)
        self.assertRegex(complaint.complaint_id, rf"^CMP-{year}-\d{{6}}$")
