from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

from .managers import UserManager


class User(AbstractUser):

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("MANAGER", "Manager"),
        ("ENGINEER", "Engineer"),
        ("OFFICE", "Office Staff"),
        ("CUSTOMER", "Customer"),
    ]

    username = None

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    phone = models.CharField(
        max_length=10,
        unique=True,
        db_index=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="ENGINEER"
    )

    is_verified = models.BooleanField(
        default=False
    )

    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"

    REQUIRED_FIELDS = []

    def __str__(self):
        return (
            f"{self.first_name} "
            f"({self.phone})"
        )


class PhoneOTP(models.Model):

    MAX_ATTEMPTS = 5

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_otps",
    )

    otp = models.CharField(
        max_length=6
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0
    )

    is_used = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

    def __str__(self):
        return (
            f"{self.user.phone} - "
            f"{self.created_at}"
        )


class AuthSecurityEvent(models.Model):
    EVENT_CHOICES = [
        ("LOGIN_SUCCESS", "Login Success"),
        ("LOGIN_FAILED", "Login Failed"),
        ("ACCOUNT_LOCKED", "Account Locked"),
        ("OTP_VERIFIED", "OTP Verified"),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_events")
    event_type = models.CharField(max_length=24, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=64, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SmsGatewayDevice(models.Model):
    device_id = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    secret_hash = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=15, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.device_id})"


class SimVerificationChallenge(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sim_verification_challenges")
    token_hash = models.CharField(max_length=64, db_index=True)
    poll_secret_hash = models.CharField(max_length=64)
    pending_password_hash = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(SmsGatewayDevice, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_challenges")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class CustomerEngagement(models.Model):
    KIND_CHOICES = [
        ("OFFER", "Offer"),
        ("PAYMENT", "Payment Alert"),
        ("SERVICE", "Service Reminder"),
        ("ANNOUNCEMENT", "Announcement"),
    ]
    AUDIENCE_CHOICES = [("ALL", "All Customers"), ("TARGETED", "Targeted Customer")]
    DISCOUNT_CHOICES = [("NONE", "No Discount"), ("PERCENT", "Percentage"), ("FIXED", "Fixed Amount")]
    ACTION_CHOICES = [
        ("NONE", "No Action"),
        ("SHOP", "Open Shop"),
        ("RENT", "Pay Rent"),
        ("SERVICE", "Book Service"),
        ("REFERRAL", "Open Referral"),
    ]

    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="ANNOUNCEMENT")
    audience = models.CharField(max_length=12, choices=AUDIENCE_CHOICES, default="ALL")
    target_user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name="targeted_engagements", limit_choices_to={"role": "CUSTOMER"},
    )
    title = models.CharField(max_length=120)
    message = models.TextField(max_length=500)
    badge_text = models.CharField(max_length=30, blank=True, default="")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_CHOICES, default="NONE")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promo_code = models.CharField(max_length=30, blank=True, default="")
    terms = models.CharField(max_length=300, blank=True, default="")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=50)
    action = models.CharField(max_length=12, choices=ACTION_CHOICES, default="NONE")
    action_label = models.CharField(max_length=40, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_engagements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return self.title


class CustomerEngagementRead(models.Model):
    engagement = models.ForeignKey(CustomerEngagement, on_delete=models.CASCADE, related_name="read_receipts")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="engagement_reads")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["engagement", "user"], name="unique_engagement_read")
        ]


class SmsGatewaySubmission(models.Model):
    gateway = models.ForeignKey(SmsGatewayDevice, on_delete=models.PROTECT, related_name="submissions")
    nonce = models.CharField(max_length=64, unique=True)
    sender_phone = models.CharField(max_length=15)
    message_fingerprint = models.CharField(max_length=64)
    accepted = models.BooleanField(default=False)
    result_code = models.CharField(max_length=40)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
