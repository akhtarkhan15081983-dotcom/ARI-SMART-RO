from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class ReferralProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_profile",
    )
    referral_code = models.CharField(max_length=20, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.referral_code}"


class Referral(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("QUALIFIED", "Qualified"),
        ("REJECTED", "Rejected"),
        ("REVERSED", "Reversed"),
    ]

    CUSTOMER_TYPE_CHOICES = [
        ("RENT", "Rent Customer"),
        ("PURCHASE", "Purchase Customer"),
    ]

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referrals_made",
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referral_received",
    )
    referral_code = models.CharField(max_length=20, db_index=True)
    referred_customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="referral_record",
    )
    referred_type = models.CharField(
        max_length=10,
        choices=CUSTOMER_TYPE_CHOICES,
        blank=True,
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    qualifying_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    qualified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["referrer", "referred_user"],
                name="unique_referrer_referred_user",
            )
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.referrer_id}->{self.referred_user_id} ({self.status})"


class WalletReward(models.Model):
    REWARD_TYPES = [
        ("APP_WELCOME", "App Welcome Reward"),
        ("RENT_REFERRAL", "Rent to Rent Referral"),
        ("RENT_TO_PURCHASE", "Rent to Purchase Referral"),
        ("PURCHASE_TO_RENT", "Purchase to Rent Referral"),
        ("PURCHASE_REFERRAL", "Purchase to Purchase Referral"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("PARTIAL", "Partially Used"),
        ("USED", "Fully Used"),
        ("EXPIRED", "Expired"),
        ("REVERSED", "Reversed"),
        ("HOLD", "On Hold"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet_rewards",
    )
    referral = models.ForeignKey(
        Referral,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rewards",
    )
    reward_type = models.CharField(max_length=30, choices=REWARD_TYPES)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    used_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_bill_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    usage_categories = models.JSONField(default=list)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="ACTIVE")
    activated_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    source_reference = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.owner_id} - {self.reward_type} - {self.remaining_amount}"


class WalletLedgerEntry(models.Model):
    ENTRY_TYPES = [
        ("CREDIT", "Credit"),
        ("DEBIT", "Debit"),
        ("REVERSAL", "Reversal"),
        ("EXPIRY", "Expiry"),
        ("ADJUSTMENT", "Adjustment"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet_ledger_entries",
    )
    reward = models.ForeignKey(
        WalletReward,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(max_length=12, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_type = models.CharField(max_length=40, blank=True, default="")
    reference_id = models.CharField(max_length=80, blank=True, default="")
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user_id} - {self.entry_type} - {self.amount}"
