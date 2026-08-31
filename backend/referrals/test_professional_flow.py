from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from customers.models import Customer

from .models import Referral
from .services import (
    approve_referral_review,
    calculate_max_redeemable,
    claim_referral,
    get_or_create_profile,
    qualify_referral,
)


class ProfessionalReferralFlowTests(TestCase):
    def _customer(self, phone, name, verified=True, monthly_rent="300"):
        user = get_user_model().objects.create_user(
            phone=phone,
            password="Test@123",
            role="CUSTOMER",
            is_verified=verified,
            first_name=name,
        )
        Customer.objects.create(
            user=user,
            name=name,
            phone=phone,
            address="Test address",
            city="Bareilly",
            state="UP",
            pincode="243001",
            ro_model="ARI RO",
            monthly_rent=Decimal(monthly_rent),
        )
        return user

    def setUp(self):
        self.referrer = self._customer("9100000001", "Referrer")
        self.code = get_or_create_profile(self.referrer).referral_code

    def test_verified_claim_automatically_credits_100_points_to_referrer(self):
        referred = self._customer("9100000002", "Referred")
        referral = claim_referral(
            referred_user=referred,
            code=self.code,
            claim_fingerprint="device-one",
        )

        self.assertEqual(referral.status, "PENDING")
        reward = referral.rewards.get(reward_type="APP_REFERRAL_POINTS")
        self.assertEqual(reward.owner, self.referrer)
        self.assertEqual(reward.total_amount, Decimal("10.00"))
        self.assertEqual(reward.max_bill_percent, Decimal("30.00"))
        self.assertEqual(reward.usage_categories, ["PURCHASE", "PARTS", "SERVICE"])
        self.assertEqual(
            calculate_max_redeemable(
                user=self.referrer,
                bill_amount=Decimal("20.00"),
                category="SERVICE",
            ),
            Decimal("6.00"),
        )
        self.assertEqual(
            calculate_max_redeemable(
                user=self.referrer,
                bill_amount=Decimal("300.00"),
                category="RENT",
                reference_type="RENT_PAYMENT",
                reference_id="2026-08",
            ),
            Decimal("0.00"),
        )

    def test_same_device_exception_is_held_for_review(self):
        first = self._customer("9100000003", "First")
        second = self._customer("9100000004", "Second")
        claim_referral(referred_user=first, code=self.code, claim_fingerprint="shared-device")
        flagged = claim_referral(referred_user=second, code=self.code, claim_fingerprint="shared-device")

        self.assertEqual(flagged.status, "REVIEW")
        self.assertEqual(flagged.rewards.count(), 0)
        approved = approve_referral_review(flagged.id)
        self.assertEqual(approved.status, "PENDING")
        self.assertTrue(approved.rewards.filter(reward_type="APP_REFERRAL_POINTS").exists())

    def test_multiple_point_rewards_still_cannot_exceed_30_percent(self):
        first = self._customer("9100000007", "First Points")
        second = self._customer("9100000008", "Second Points")
        claim_referral(referred_user=first, code=self.code, claim_fingerprint="device-a")
        claim_referral(referred_user=second, code=self.code, claim_fingerprint="device-b")
        self.assertEqual(
            calculate_max_redeemable(
                user=self.referrer,
                bill_amount=Decimal("50.00"),
                category="SERVICE",
            ),
            Decimal("15.00"),
        )

    def test_unverified_account_cannot_claim(self):
        referred = self._customer("9100000005", "Unverified", verified=False)
        with self.assertRaises(Exception):
            claim_referral(referred_user=referred, code=self.code)

    def test_installation_qualification_adds_rent_benefit_after_points(self):
        referred = self._customer("9100000006", "Installed")
        referral = claim_referral(referred_user=referred, code=self.code)
        qualify_referral(referral.id, referred_type="RENT", qualifying_amount=Decimal("300"))

        referral.refresh_from_db()
        self.assertEqual(referral.status, "QUALIFIED")
        self.assertEqual(
            set(referral.rewards.values_list("reward_type", flat=True)),
            {"APP_REFERRAL_POINTS", "RENT_REFERRAL"},
        )
        self.assertEqual(
            referral.rewards.get(reward_type="RENT_REFERRAL").total_amount,
            Decimal("600.00"),
        )
