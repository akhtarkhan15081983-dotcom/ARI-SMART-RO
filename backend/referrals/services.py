from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    ReferralProfile,
    Referral,
    WalletReward,
    WalletLedgerEntry,
)


# ============================================================
# REWARD CONFIGURATION
# ============================================================

WELCOME_AMOUNT = Decimal("50.00")
WELCOME_VALIDITY_DAYS = 90
WELCOME_MAX_BILL_PERCENT = Decimal("40.00")


# ------------------------------------------------------------
# RENT REFERRAL
#
# ₹50 per month x 12 months = ₹600
# ------------------------------------------------------------

RENT_REFERRAL_MONTHLY = Decimal("50.00")

RENT_REFERRAL_MONTHS = 12

RENT_REFERRAL_TOTAL = (
    RENT_REFERRAL_MONTHLY
    * RENT_REFERRAL_MONTHS
)


# ------------------------------------------------------------
# RENT CUSTOMER MUST ALWAYS PAY AT LEAST ₹100
# ------------------------------------------------------------

MIN_RENT_PAYABLE = Decimal("100.00")


# ------------------------------------------------------------
# RENT REFERRAL REWARD VALIDITY
# ------------------------------------------------------------

RENT_REFERRAL_VALIDITY_DAYS = 365


# ------------------------------------------------------------
# EXISTING BUSINESS RULE
# ------------------------------------------------------------

RENT_TO_PURCHASE_PERCENT = Decimal("15.00")


# ============================================================
# WALLET CATEGORIES
# ============================================================

CATEGORY_RENT = "RENT"
CATEGORY_PURCHASE = "PURCHASE"
CATEGORY_PARTS = "PARTS"
CATEGORY_SERVICE = "SERVICE"


# ============================================================
# RENT REFERRAL REWARD TYPES
# ============================================================
#
# These rewards represent the ₹50 x 12 month rent benefit.
#
# RENT_TO_PURCHASE is intentionally NOT included because its
# existing business rule is percentage based.
# ============================================================

MONTHLY_RENT_REWARD_TYPES = {
    "RENT_REFERRAL",
    "PURCHASE_TO_RENT",
}


# ============================================================
# REFERRAL CODE
# ============================================================

def _generate_code():

    while True:

        code = (
            "ARI"
            + uuid4().hex[:7].upper()
        )

        if not ReferralProfile.objects.filter(
            referral_code=code
        ).exists():

            return code


# ============================================================
# REFERRAL PROFILE
# ============================================================

def get_or_create_profile(user):

    profile, _ = (
        ReferralProfile.objects.get_or_create(
            user=user,
            defaults={
                "referral_code": _generate_code()
            },
        )
    )

    return profile


# ============================================================
# CLAIM REFERRAL
# ============================================================

@transaction.atomic
def claim_referral(
    *,
    referred_user,
    code,
):

    code = (
        code or ""
    ).strip().upper()

    if not code:

        raise ValidationError(
            {
                "referral_code":
                    "Referral code is required."
            }
        )

    if referred_user.role != "CUSTOMER":

        raise ValidationError(
            "Only customer accounts can join "
            "the referral program."
        )

    referrer_profile = (
        ReferralProfile.objects
        .select_related("user")
        .filter(
            referral_code=code
        )
        .first()
    )

    if not referrer_profile:

        raise ValidationError(
            {
                "referral_code":
                    "Invalid referral code."
            }
        )

    # ========================================================
    # SELF REFERRAL PROTECTION
    # ========================================================

    if (
        referrer_profile.user_id
        == referred_user.id
    ):

        raise ValidationError(
            {
                "referral_code":
                    "Self-referral is not allowed."
            }
        )

    # ========================================================
    # ONE ACTIVE ATTRIBUTION PER CUSTOMER
    # ========================================================

    if (
        Referral.objects
        .filter(
            referred_user=referred_user
        )
        .exclude(
            status="REJECTED"
        )
        .exists()
    ):

        raise ValidationError(
            "This customer already has "
            "a referral attribution."
        )

    return Referral.objects.create(
        referrer=referrer_profile.user,
        referred_user=referred_user,
        referral_code=code,
    )


# ============================================================
# CUSTOMER TYPE
# ============================================================

def _customer_type(customer):
    """
    Positive monthly_rent
        -> RENT customer

    Zero / empty monthly_rent
        -> PURCHASE customer
    """

    rent = Decimal(
        str(
            customer.monthly_rent or 0
        )
    )

    return (
        "RENT"
        if rent > 0
        else "PURCHASE"
    )


# ============================================================
# CREATE WALLET REWARD
# ============================================================

def _create_reward(
    *,
    owner,
    reward_type,
    amount,
    categories,
    referral=None,
    max_bill_percent=None,
    expires_at=None,
    source_reference="",
):

    reward = WalletReward.objects.create(

        owner=owner,

        referral=referral,

        reward_type=reward_type,

        total_amount=amount,

        used_amount=Decimal("0.00"),

        remaining_amount=amount,

        max_bill_percent=max_bill_percent,

        usage_categories=categories,

        status="ACTIVE",

        expires_at=expires_at,

        source_reference=source_reference,
    )

    # ========================================================
    # CREDIT LEDGER
    # ========================================================

    WalletLedgerEntry.objects.create(

        user=owner,

        reward=reward,

        entry_type="CREDIT",

        amount=amount,

        reference_type="REWARD",

        reference_id=str(
            reward.id
        ),

        description=(
            f"{reward.get_reward_type_display()} "
            "credited."
        ),
    )

    return reward


# ============================================================
# WELCOME REWARD
# ============================================================

@transaction.atomic
def claim_welcome_reward(user):
    """
    One-time server-side welcome reward.

    Amount:
        ₹50

    Validity:
        90 days

    Usage:
        PURCHASE
        PARTS
        SERVICE

    NOT allowed:
        RENT
    """

    if (
        user.role != "CUSTOMER"
        or not user.is_verified
    ):

        raise ValidationError(
            "Verified customer account is required."
        )

    # ========================================================
    # PREVENT DUPLICATE WELCOME REWARD
    # ========================================================

    existing = (
        WalletReward.objects
        .filter(
            owner=user,
            reward_type="APP_WELCOME",
        )
        .exists()
    )

    if existing:

        raise ValidationError(
            "Welcome reward has already been claimed."
        )

    # ========================================================
    # CUSTOMER PROFILE REQUIRED
    # ========================================================

    from customers.models import Customer

    customer = (
        Customer.objects
        .filter(
            user=user
        )
        .first()
    )

    if customer is None:

        raise ValidationError(
            "Customer profile is required "
            "before claiming the welcome reward."
        )

    # ========================================================
    # 90 DAY EXPIRY
    # ========================================================

    expires_at = (
        timezone.now()
        + timezone.timedelta(
            days=WELCOME_VALIDITY_DAYS
        )
    )

    return _create_reward(

        owner=user,

        reward_type="APP_WELCOME",

        amount=WELCOME_AMOUNT,

        categories=[
            CATEGORY_PURCHASE,
            CATEGORY_PARTS,
            CATEGORY_SERVICE,
        ],

        max_bill_percent=(
            WELCOME_MAX_BILL_PERCENT
        ),

        expires_at=expires_at,

        source_reference=(
            "APP_DOWNLOAD_WELCOME"
        ),
    )


# ============================================================
# QUALIFY REFERRAL
# ============================================================

@transaction.atomic
def qualify_referral(
    referral_id,
    *,
    referred_type,
    qualifying_amount=Decimal("0.00"),
    actor=None,
):

    referral = (
        Referral.objects
        .select_for_update()
        .select_related(
            "referrer",
            "referred_user",
        )
        .get(
            pk=referral_id
        )
    )

    # ========================================================
    # ONLY PENDING REFERRALS
    # ========================================================

    if referral.status != "PENDING":

        raise ValidationError(
            "Only pending referrals can be qualified."
        )

    # ========================================================
    # VALID CUSTOMER TYPE
    # ========================================================

    if referred_type not in {
        "RENT",
        "PURCHASE",
    }:

        raise ValidationError(
            "Invalid referred customer type."
        )

    # ========================================================
    # QUALIFYING AMOUNT
    # ========================================================

    amount = Decimal(
        str(
            qualifying_amount or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    # ========================================================
    # QUALIFY REFERRAL
    # ========================================================

    referral.referred_type = (
        referred_type
    )

    referral.qualifying_amount = (
        amount
    )

    referral.status = "QUALIFIED"

    referral.qualified_at = (
        timezone.now()
    )

    referral.save(
        update_fields=[
            "referred_type",
            "qualifying_amount",
            "status",
            "qualified_at",
            "updated_at",
        ]
    )

    # ========================================================
    # DUPLICATE REWARD PROTECTION
    # ========================================================

    if referral.rewards.exists():

        return referral

    # ========================================================
    # DETERMINE REFERRER TYPE
    # ========================================================

    referrer_type = "PURCHASE"

    from customers.models import Customer

    customer = (
        Customer.objects
        .filter(
            user=referral.referrer
        )
        .first()
    )

    if customer is not None:

        referrer_type = _customer_type(
            customer
        )

    # ========================================================
    # 12-MONTH RENT REFERRAL EXPIRY
    # ========================================================

    rent_referral_expires_at = (
        timezone.now()
        + timezone.timedelta(
            days=RENT_REFERRAL_VALIDITY_DAYS
        )
    )

    # ========================================================
    # RENT -> RENT
    #
    # ₹600 total
    # ₹50 x 12 months
    # RENT only
    # Valid for 12 months
    # ========================================================

    if (
        referrer_type == "RENT"
        and referred_type == "RENT"
    ):

        _create_reward(

            owner=referral.referrer,

            reward_type="RENT_REFERRAL",

            amount=RENT_REFERRAL_TOTAL,

            categories=[
                CATEGORY_RENT
            ],

            referral=referral,

            expires_at=(
                rent_referral_expires_at
            ),

            source_reference=(
                f"REFERRAL:{referral.id}"
            ),
        )

    # ========================================================
    # RENT -> PURCHASE
    #
    # Existing business rule retained.
    # ========================================================

    elif (
        referrer_type == "RENT"
        and referred_type == "PURCHASE"
    ):

        reward_amount = (
            amount
            * RENT_TO_PURCHASE_PERCENT
            / Decimal("100")
        ).quantize(
            Decimal("0.01")
        )

        if reward_amount > 0:

            _create_reward(

                owner=referral.referrer,

                reward_type="RENT_TO_PURCHASE",

                amount=reward_amount,

                categories=[
                    CATEGORY_RENT
                ],

                referral=referral,

                source_reference=(
                    f"REFERRAL:{referral.id}"
                ),
            )

    # ========================================================
    # PURCHASE -> RENT
    #
    # ₹600 total
    # ₹50 x 12 months
    # RENT only
    # Valid for 12 months
    # ========================================================

    elif (
        referrer_type == "PURCHASE"
        and referred_type == "RENT"
    ):

        _create_reward(

            owner=referral.referrer,

            reward_type="PURCHASE_TO_RENT",

            amount=RENT_REFERRAL_TOTAL,

            categories=[
                CATEGORY_RENT
            ],

            referral=referral,

            expires_at=(
                rent_referral_expires_at
            ),

            source_reference=(
                f"REFERRAL:{referral.id}"
            ),
        )

    # ========================================================
    # PURCHASE -> PURCHASE
    #
    # No fixed amount currently defined.
    # ========================================================

    else:

        pass

    return referral


# ============================================================
# EXPIRE WALLET REWARDS
# ============================================================

@transaction.atomic
def expire_rewards(now=None):

    now = (
        now
        or timezone.now()
    )

    rewards = (
        WalletReward.objects
        .filter(
            status__in=[
                "ACTIVE",
                "PARTIAL",
            ],
            expires_at__isnull=False,
            expires_at__lte=now,
            remaining_amount__gt=0,
        )
    )

    count = 0

    for reward in (
        rewards
        .select_for_update()
    ):

        remaining = (
            reward.remaining_amount
        )

        reward.status = "EXPIRED"

        reward.remaining_amount = (
            Decimal("0.00")
        )

        reward.save(
            update_fields=[
                "status",
                "remaining_amount",
                "updated_at",
            ]
        )

        # ====================================================
        # EXPIRY LEDGER
        # ====================================================

        WalletLedgerEntry.objects.create(

            user=reward.owner,

            reward=reward,

            entry_type="EXPIRY",

            amount=remaining,

            reference_type=(
                "REWARD_EXPIRY"
            ),

            reference_id=str(
                reward.id
            ),

            description=(
                "Reward expired after "
                "its validity period."
            ),
        )

        count += 1

    return count


# ============================================================
# RENT REFERRAL MONTHLY USAGE
# ============================================================

def _get_rent_referral_monthly_used(
    *,
    user,
    reference_type,
    reference_id,
):
    """
    Returns how much monthly rent-referral wallet
    benefit has already been consumed for the same
    rent period.

    Production convention:

        reference_type = "RENT_PAYMENT"
        reference_id   = "YYYY-MM"

    Example:

        RENT_PAYMENT / 2026-08

    Only RENT_REFERRAL and PURCHASE_TO_RENT rewards
    are counted here.

    RENT_TO_PURCHASE is intentionally excluded because
    that reward follows its separate percentage-based
    business rule.
    """

    if (
        reference_type != "RENT_PAYMENT"
        or not reference_id
    ):

        return Decimal("0.00")

    used = (
        WalletLedgerEntry.objects
        .filter(
            user=user,
            entry_type="DEBIT",
            reference_type="RENT_PAYMENT",
            reference_id=str(
                reference_id
            ),
            reward__reward_type__in=(
                MONTHLY_RENT_REWARD_TYPES
            ),
        )
        .aggregate(
            total=Sum("amount")
        )
        .get("total")
    )

    return (
        Decimal(str(used))
        if used is not None
        else Decimal("0.00")
    )


# ============================================================
# CALCULATE MAX REDEEMABLE
# ============================================================

def calculate_max_redeemable(
    *,
    user,
    bill_amount,
    category,
    reference_type=None,
    reference_id=None,
):
    """
    Returns the server-authorized maximum wallet amount
    for an eligible bill.

    RENT rules:

        - Customer must pay at least ₹100.
        - Monthly referral wallet benefit is maximum ₹50.
        - Same rent period cannot consume more than ₹50.

    reference_type/reference_id are optional for backward
    compatibility with existing callers.

    For exact monthly RENT quote, caller should provide:

        reference_type="RENT_PAYMENT"
        reference_id="YYYY-MM"
    """

    bill = Decimal(
        str(
            bill_amount or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    if bill <= 0:

        return Decimal("0.00")

    # ========================================================
    # SPENDING CEILING
    # ========================================================

    spend_ceiling = bill

    monthly_rent_remaining = (
        RENT_REFERRAL_MONTHLY
    )

    if category == CATEGORY_RENT:

        # ----------------------------------------------------
        # Customer must pay minimum ₹100.
        # ----------------------------------------------------

        minimum_payable_ceiling = max(
            bill - MIN_RENT_PAYABLE,
            Decimal("0.00"),
        )

        # ----------------------------------------------------
        # Maximum monthly referral benefit = ₹50.
        # ----------------------------------------------------

        spend_ceiling = min(
            minimum_payable_ceiling,
            RENT_REFERRAL_MONTHLY,
        )

        # ----------------------------------------------------
        # Existing usage for this rent month.
        # ----------------------------------------------------

        monthly_used = (
            _get_rent_referral_monthly_used(
                user=user,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        )

        monthly_rent_remaining = max(
            RENT_REFERRAL_MONTHLY
            - monthly_used,
            Decimal("0.00"),
        )

        spend_ceiling = min(
            spend_ceiling,
            monthly_rent_remaining,
        )

    # ========================================================
    # EXPIRE OLD REWARDS
    # ========================================================

    expire_rewards()

    rewards = (
        WalletReward.objects
        .filter(
            owner=user,
            status__in=[
                "ACTIVE",
                "PARTIAL",
            ],
            remaining_amount__gt=0,
        )
        .order_by(
            "activated_at",
            "id",
        )
    )

    total = Decimal("0.00")

    for reward in rewards:

        # ====================================================
        # CATEGORY CHECK
        # ====================================================

        if category not in (
            reward.usage_categories
        ):

            continue

        available = (
            reward.remaining_amount
        )

        # ====================================================
        # RENT MONTHLY REWARD LIMIT
        # ====================================================

        if (
            category == CATEGORY_RENT
            and reward.reward_type
            in MONTHLY_RENT_REWARD_TYPES
        ):

            available = min(
                available,
                monthly_rent_remaining,
            )

        # ====================================================
        # BILL PERCENTAGE CAP
        # ====================================================

        if (
            reward.max_bill_percent
            is not None
        ):

            cap = (
                bill
                * reward.max_bill_percent
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_DOWN,
            )

            available = min(
                available,
                (
                    cap - total
                    if cap > total
                    else Decimal("0.00")
                ),
            )

        total += max(
            available,
            Decimal("0.00"),
        )

        if total >= spend_ceiling:

            return spend_ceiling

    return min(
        total,
        spend_ceiling,
    )


# ============================================================
# REDEEM WALLET
# ============================================================

@transaction.atomic
def redeem_wallet(
    *,
    user,
    bill_amount,
    category,
    reference_type,
    reference_id,
):
    """
    Atomically consumes rewards FIFO.

    Caller must separately settle the remaining
    cash / UPI amount.

    RENT:

        - Maximum referral wallet use = ₹50 per month.
        - Customer payable minimum = ₹100.
        - Same rent period cannot consume another ₹50.
        - Next rent month can consume another ₹50.

    Production convention:

        reference_type = "RENT_PAYMENT"
        reference_id   = "YYYY-MM"

    Example:

        August:
            RENT_PAYMENT / 2026-08

        September:
            RENT_PAYMENT / 2026-09
    """

    bill = Decimal(
        str(
            bill_amount or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    if bill <= 0:

        raise ValidationError(
            "Bill amount must be greater than zero."
        )

    # ========================================================
    # REQUIRED REFERENCE FOR RENT
    # ========================================================

    if category == CATEGORY_RENT:

        if (
            not reference_type
            or not reference_id
        ):

            raise ValidationError(
                "reference_type and reference_id "
                "are required for rent wallet redemption."
            )

    # ========================================================
    # SPENDING CEILING
    # ========================================================

    spend_ceiling = bill

    monthly_rent_used = Decimal("0.00")

    monthly_rent_remaining = (
        RENT_REFERRAL_MONTHLY
    )

    if category == CATEGORY_RENT:

        # ----------------------------------------------------
        # Customer must pay minimum ₹100.
        # ----------------------------------------------------

        minimum_payable_ceiling = max(
            bill - MIN_RENT_PAYABLE,
            Decimal("0.00"),
        )

        # ----------------------------------------------------
        # Maximum monthly referral benefit = ₹50.
        # ----------------------------------------------------

        spend_ceiling = min(
            minimum_payable_ceiling,
            RENT_REFERRAL_MONTHLY,
        )

        # ----------------------------------------------------
        # Existing monthly usage.
        # ----------------------------------------------------

        monthly_rent_used = (
            _get_rent_referral_monthly_used(
                user=user,
                reference_type=reference_type,
                reference_id=reference_id,
            )
        )

        monthly_rent_remaining = max(
            RENT_REFERRAL_MONTHLY
            - monthly_rent_used,
            Decimal("0.00"),
        )

        # ----------------------------------------------------
        # If this month's ₹50 has already been used,
        # nothing more can be redeemed.
        # ----------------------------------------------------

        spend_ceiling = min(
            spend_ceiling,
            monthly_rent_remaining,
        )

    # ========================================================
    # EXPIRE OLD REWARDS
    # ========================================================

    expire_rewards()

    # ========================================================
    # LOCK REWARDS
    #
    # FIFO:
    # Oldest reward is consumed first.
    # ========================================================

    rewards = list(
        WalletReward.objects
        .select_for_update()
        .filter(
            owner=user,
            status__in=[
                "ACTIVE",
                "PARTIAL",
            ],
            remaining_amount__gt=0,
        )
        .order_by(
            "activated_at",
            "id",
        )
    )

    remaining_bill = (
        spend_ceiling
    )

    consumed = Decimal("0.00")

    lines = []

    # ========================================================
    # CONSUME REWARDS
    # ========================================================

    for reward in rewards:

        # ====================================================
        # CATEGORY ELIGIBILITY
        # ====================================================

        if category not in (
            reward.usage_categories
        ):

            continue

        reward_available = (
            reward.remaining_amount
        )

        # ====================================================
        # RENT MONTHLY LIMIT
        #
        # Only monthly rent-referral rewards are limited by
        # the ₹50 monthly allowance.
        #
        # RENT_TO_PURCHASE remains governed by its own
        # existing percentage-based reward rule.
        # ====================================================

        if (
            category == CATEGORY_RENT
            and reward.reward_type
            in MONTHLY_RENT_REWARD_TYPES
        ):

            reward_available = min(
                reward_available,
                monthly_rent_remaining,
            )

        # ====================================================
        # BILL PERCENTAGE CAP
        # ====================================================

        if (
            reward.max_bill_percent
            is not None
        ):

            cap = (
                bill
                * reward.max_bill_percent
                / Decimal("100")
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_DOWN,
            )

            already = sum(
                x[1]
                for x in lines
                if x[0]
                == reward.reward_type
            )

            reward_available = min(
                reward_available,
                max(
                    cap - already,
                    Decimal("0.00"),
                ),
            )

        # ====================================================
        # CURRENT REWARD USAGE
        # ====================================================

        use = min(
            reward_available,
            remaining_bill,
        )

        if use <= 0:

            continue

        # ====================================================
        # UPDATE REWARD BALANCE
        # ====================================================

        reward.used_amount += use

        reward.remaining_amount -= use

        if (
            reward.remaining_amount
            == Decimal("0.00")
        ):

            reward.status = "USED"

        else:

            reward.status = "PARTIAL"

        reward.save(
            update_fields=[
                "used_amount",
                "remaining_amount",
                "status",
                "updated_at",
            ]
        )

        # ====================================================
        # DEBIT LEDGER
        # ====================================================

        WalletLedgerEntry.objects.create(

            user=user,

            reward=reward,

            entry_type="DEBIT",

            amount=use,

            reference_type=reference_type,

            reference_id=str(
                reference_id
            ),

            description=(
                f"Wallet reward used for "
                f"{category} transaction."
            ),
        )

        # ====================================================
        # UPDATE TOTALS
        # ====================================================

        consumed += use

        remaining_bill -= use

        lines.append(
            (
                reward.reward_type,
                use,
                reward.id,
            )
        )

        # ----------------------------------------------------
        # Monthly rent usage is now increased immediately.
        # ----------------------------------------------------

        if (
            category == CATEGORY_RENT
            and reward.reward_type
            in MONTHLY_RENT_REWARD_TYPES
        ):

            monthly_rent_remaining = max(
                monthly_rent_remaining - use,
                Decimal("0.00"),
            )

        if remaining_bill <= 0:

            break

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {

        "bill_amount":
            bill,

        "wallet_used":
            consumed,

        "customer_payable":
            max(
                bill - consumed,
                Decimal("0.00"),
            ),

        "lines":
            lines,
    }