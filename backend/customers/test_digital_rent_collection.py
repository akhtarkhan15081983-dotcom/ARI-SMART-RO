from datetime import date

from django.test import SimpleTestCase

from .rent_management_optimized import _collection_bucket


class DigitalRentCollectionBucketTests(SimpleTestCase):
    def setUp(self):
        self.today = date(2026, 9, 26)

    def test_paid_customer_is_collected(self):
        self.assertEqual(
            _collection_bucket('PAID', 0, self.today, self.today),
            'COLLECTED',
        )

    def test_zero_balance_is_collected(self):
        self.assertEqual(
            _collection_bucket('PARTIAL', 0, self.today, self.today),
            'COLLECTED',
        )

    def test_due_today(self):
        self.assertEqual(
            _collection_bucket('PENDING', 900, self.today, self.today),
            'TODAY',
        )

    def test_overdue(self):
        self.assertEqual(
            _collection_bucket('PENDING', 900, date(2026, 9, 20), self.today),
            'OVERDUE',
        )

    def test_due_within_next_seven_days(self):
        self.assertEqual(
            _collection_bucket('PENDING', 900, date(2026, 10, 2), self.today),
            'NEXT_7_DAYS',
        )

    def test_later_due_is_upcoming(self):
        self.assertEqual(
            _collection_bucket('PENDING', 900, date(2026, 10, 10), self.today),
            'UPCOMING',
        )
