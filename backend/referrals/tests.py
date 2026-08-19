from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from customers.models import Customer

from .models import (
    ReferralProfile,
    Referral,
    WalletReward,
    WalletLedgerEntry,
)

from .services import (
    get_or_create_profile,
    claim_welcome_reward,
    qualify_referral,
    redeem_wallet,
)


class ReferralWalletTests(TestCase):

    def setUp(self):

        User = get_user_model()

        # ----------------------------------------------------
        # REFERRER
        # ----------------------------------------------------

        self.referrer = User.objects.create_user(
            phone="9000000001",
            password="Test@123",
            role="CUSTOMER",
            is_verified=True,
        )

        # ----------------------------------------------------
        # REFERRED CUSTOMER
        # ----------------------------------------------------

        self.referred = User.objects.create_user(
            phone="9000000002",
            password="Test@123",
            role="CUSTOMER",
            is_verified=True,
        )

        # ----------------------------------------------------
        # REFERRER CUSTOMER PROFILE
        # ----------------------------------------------------

        self.referrer_customer = Customer.objects.create(
            user=self.referrer,
            name="Referrer",
            phone=self.referrer.phone,
            address="A",
            city="Agra",
            state="UP",
            pincode="282001",
            ro_model="RO",
            monthly_rent=Decimal("300"),
        )

        # ----------------------------------------------------
        # REFERRED CUSTOMER PROFILE
        # ----------------------------------------------------

        self.referred_customer = Customer.objects.create(
            user=self.referred,
            name="Referred",
            phone=self.referred.phone,
            address="B",
            city="Agra",
            state="UP",
            pincode="282001",
            ro_model="RO",
            monthly_rent=Decimal("300"),
        )

        # ----------------------------------------------------
        # REFERRAL PROFILE
        # ----------------------------------------------------

        self.profile = get_or_create_profile(
            self.referrer
        )

    # ========================================================
    # REFERRAL PROFILE
    # ========================================================

    def test_referral_code_is_unique(self):

        self.assertEqual(
            ReferralProfile.objects.filter(
                user=self.referrer
            ).count(),
            1,
        )

        self.assertEqual(
            len(self.profile.referral_code),
            10,
        )

    # ========================================================
    # WELCOME REWARD
    # ========================================================

    def test_welcome_reward_is_50_and_40_percent_capped(self):

        reward = claim_welcome_reward(
            self.referred
        )

        self.assertEqual(
            reward.total_amount,
            Decimal("50.00"),
        )

        self.assertEqual(
            reward.max_bill_percent,
            Decimal("40.00"),
        )

        result = redeem_wallet(
            user=self.referred,
            bill_amount=Decimal("1000"),
            category="SERVICE",
            reference_type="TEST",
            reference_id="1",
        )

        self.assertEqual(
            result["wallet_used"],
            Decimal("50.00"),
        )

    # ========================================================
    # RENT -> RENT REFERRAL
    # ========================================================

    def test_rent_to_rent_gives_600(self):

        referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code=self.profile.referral_code,
        )

        qualify_referral(
            referral.id,
            referred_type="RENT",
            qualifying_amount=Decimal("0"),
        )

        reward = referral.rewards.get()

        self.assertEqual(
            reward.total_amount,
            Decimal("600.00"),
        )

        self.assertEqual(
            reward.usage_categories,
            ["RENT"],
        )

    # ========================================================
    # RENT REFERRAL:
    # MAX ₹50 PER MONTHLY RENT
    # ========================================================

    def test_rent_referral_can_use_max_50_per_monthly_rent(self):

        referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code=self.profile.referral_code,
        )

        qualify_referral(
            referral.id,
            referred_type="RENT",
            qualifying_amount=Decimal("0"),
        )

        result = redeem_wallet(
            user=self.referrer,
            bill_amount=Decimal("300"),
            category="RENT",
            reference_type="RENT_PAYMENT",
            reference_id="RENT-1",
        )

        self.assertEqual(
            result["wallet_used"],
            Decimal("50.00"),
        )

        reward = referral.rewards.get()

        self.assertEqual(
            reward.remaining_amount,
            Decimal("550.00"),
        )

    def test_rent_referral_cannot_use_more_than_50_for_same_month(self):

        referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code=self.profile.referral_code,
        )

        qualify_referral(
            referral.id,
            referred_type="RENT",
            qualifying_amount=Decimal("0"),
        )

        first = redeem_wallet(
            user=self.referrer,
            bill_amount=Decimal("300"),
            category="RENT",
            reference_type="RENT_PAYMENT",
            reference_id="2026-08",
        )

        self.assertEqual(
            first["wallet_used"],
            Decimal("50.00"),
        )

        # Same rent month:
        # wallet se aur ₹50 nahi milna chahiye.
        second = redeem_wallet(
            user=self.referrer,
            bill_amount=Decimal("300"),
            category="RENT",
            reference_type="RENT_PAYMENT",
            reference_id="2026-08",
        )

        self.assertEqual(
            second["wallet_used"],
            Decimal("0.00"),
        )

        reward = referral.rewards.get()

        self.assertEqual(
            reward.remaining_amount,
            Decimal("550.00"),
        )
    # ========================================================
    # RENT REFERRAL:
    # EXPIRES AFTER 12 MONTHS
    # ========================================================

    def test_rent_referral_reward_expires_in_12_months(self):

        before = timezone.now()

        referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code=self.profile.referral_code,
        )

        qualify_referral(
            referral.id,
            referred_type="RENT",
            qualifying_amount=Decimal("0"),
        )

        reward = referral.rewards.get()

        after = timezone.now()

        expected_min = (
            before
            + timedelta(days=365)
        )

        expected_max = (
            after
            + timedelta(days=365)
        )

        self.assertIsNotNone(
            reward.expires_at
        )

        self.assertGreaterEqual(
            reward.expires_at,
            expected_min,
        )

        self.assertLessEqual(
            reward.expires_at,
            expected_max,
        )

    # ========================================================
    # RENT:
    # CUSTOMER PAYABLE CANNOT GO BELOW ₹100
    # ========================================================

    def test_rent_wallet_cannot_reduce_payable_below_100(self):

        referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code=self.profile.referral_code,
        )

        qualify_referral(
            referral.id,
            referred_type="RENT",
            qualifying_amount=Decimal("0"),
        )

        result = redeem_wallet(
            user=self.referrer,
            bill_amount=Decimal("120"),
            category="RENT",
            reference_type="RENT_PAYMENT",
            reference_id="RENT-2",
        )

        self.assertEqual(
            result["wallet_used"],
            Decimal("20.00"),
        )

        self.assertEqual(
            result["customer_payable"],
            Decimal("100.00"),
        )

    # ========================================================
    # SELF REFERRAL
    # ========================================================

    def test_self_referral_is_rejected(self):

        client = APIClient()

        client.force_authenticate(
            self.referrer
        )

        response = client.post(
            "/api/referrals/claim/",
            {
                "referral_code":
                    self.profile.referral_code,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    # ========================================================
    # NO CASH WITHDRAWAL
    # ========================================================

    def test_no_cash_withdrawal_endpoint_is_exposed(self):

        client = APIClient()

        client.force_authenticate(
            self.referrer
        )

        response = client.post(
            "/api/referrals/wallet/withdraw/",
            {
                "amount": "10",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )