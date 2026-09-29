from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from customers.models import Customer


class VisibleIdAllocatorConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def _create_customer(self, index):
        close_old_connections()
        try:
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
        finally:
            close_old_connections()

    def test_simultaneous_customer_creates_never_duplicate_visible_ids(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(self._create_customer, range(16)))

        ids = [customer_id for customer_id, _ in results]
        cards = [card for _, card in results]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(cards), len(set(cards)))
        year = timezone.now().year
        self.assertTrue(all(value.startswith(f"CUS-{year}-") for value in ids))
        self.assertTrue(all(value.startswith(f"ARI-{year}-") for value in cards))

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
