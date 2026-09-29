import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from partmaster.models import PartCategory, PartMaster
from purchase.models import Purchase, Supplier
from tenancy.models import Company, CompanyMembership


class DuplicateInvoiceConcurrencyTests(TransactionTestCase):
    reset_sequences = True
    ATTEMPT_COUNT = 20

    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(
            name="Invoice Concurrency Tenant",
            slug="invoice-concurrency-tenant",
            phone="9000013001",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9899100001",
            password="InvoiceGate@123",
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
        self.supplier = Supplier.objects.create(
            company=self.company,
            name="Concurrent Supplier",
        )
        category = PartCategory.objects.create(name="Concurrent Invoice Parts")
        self.part = PartMaster.objects.create(
            name="Concurrent Filter",
            code="CONC-FLTR",
            category=category,
            is_serialized=False,
        )

    def _client(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        return client

    def _manual_attempt(self, index):
        close_old_connections()
        try:
            invoice = " INV  100 " if index % 2 == 0 else "inv100"
            response = self._client().post(
                "/api/purchases/",
                {
                    "supplier": self.supplier.id,
                    "invoice_number": invoice,
                    "invoice_date": "2026-09-29",
                    "remarks": f"manual attempt {index}",
                    "items": [
                        {
                            "part": self.part.id,
                            "quantity": 1,
                            "purchase_price": "100.00",
                        }
                    ],
                },
                format="json",
            )
            return response.status_code
        finally:
            close_old_connections()

    def _ocr_attempt(self, index):
        close_old_connections()
        try:
            invoice = " OCR  200 " if index % 2 == 0 else "ocr200"
            payload = {
                "supplier": self.supplier.id,
                "invoice_number": invoice,
                "invoice_date": "2026-09-29",
                "remarks": f"ocr attempt {index}",
                "ocr_confidence": 99,
                "items": [
                    {
                        "part": self.part.id,
                        "quantity": 1,
                        "purchase_price": "125.00",
                    }
                ],
            }
            response = self._client().post(
                "/api/purchases/invoice-scan/confirm/",
                {
                    "payload": json.dumps(payload),
                    "ocr_text": "Concurrent Supplier Invoice OCR 200 filter 1 125.00",
                },
                format="multipart",
            )
            return response.status_code
        finally:
            close_old_connections()

    def _run_parallel(self, callable_):
        with ThreadPoolExecutor(max_workers=self.ATTEMPT_COUNT) as executor:
            return list(executor.map(callable_, range(self.ATTEMPT_COUNT)))

    def test_twenty_parallel_manual_posts_create_exactly_one_purchase(self):
        statuses = self._run_parallel(self._manual_attempt)

        self.assertEqual(statuses.count(201), 1)
        self.assertEqual(len(statuses), self.ATTEMPT_COUNT)
        self.assertEqual(
            Purchase.objects.filter(company=self.company, supplier=self.supplier).count(),
            1,
        )

    def test_twenty_parallel_ocr_posts_create_exactly_one_purchase(self):
        statuses = self._run_parallel(self._ocr_attempt)

        self.assertEqual(statuses.count(201), 1)
        self.assertEqual(len(statuses), self.ATTEMPT_COUNT)
        self.assertEqual(
            Purchase.objects.filter(company=self.company, supplier=self.supplier).count(),
            1,
        )
