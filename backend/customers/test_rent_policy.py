from datetime import date, datetime
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from .rent_policy import rent_alert_schedule, rent_penalty


class RentPolicyTests(SimpleTestCase):
    def test_penalty_starts_after_three_full_grace_days(self):
        due = date(2026, 9, 10)
        self.assertEqual(
            rent_penalty(Decimal("500"), due, date(2026, 9, 13))["penalty_amount"],
            Decimal("0.00"),
        )
        result = rent_penalty(Decimal("500"), due, date(2026, 9, 14))
        self.assertEqual(result["penalty_days"], 1)
        self.assertEqual(result["penalty_amount"], Decimal("10.00"))

    def test_paid_rent_never_gets_penalty(self):
        result = rent_penalty(Decimal("0"), date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(result["penalty_amount"], Decimal("0.00"))

    def test_alert_window_begins_three_days_before_due(self):
        now = timezone.make_aware(datetime(2026, 9, 7, 1, 0))
        result = rent_alert_schedule(date(2026, 9, 10), now)
        self.assertTrue(result["active"])
        self.assertEqual(result["repeat_interval_hours"], 3)
