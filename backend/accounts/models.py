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
        ("CALLING", "Calling Staff"),
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
        ("JOB_OTP_ADMIN_VIEWED", "Job OTP Admin Viewed"),
        ("PASSWORD_RESET_REQUESTED", "Password Reset Requested"),
        ("PASSWORD_RESET_APPROVED", "Password Reset Approved"),
        ("PASSWORD_RESET_REJECTED", "Password Reset Rejected"),
        ("PASSWORD_RESET_COMPLETED", "Password Reset Completed"),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="security_events")
    event_type = models.CharField(max_length=24, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=64, blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PasswordResetRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("USED", "Used"),
        ("EXPIRED", "Expired"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_requests",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    requested_device_id = models.CharField(max_length=64, blank=True, default="")
    code_hash = models.CharField(max_length=128, blank=True, default="")
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_password_reset_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="acct_pwdreset_status_idx"),
            models.Index(fields=["user", "created_at"], name="acct_pwdreset_user_idx"),
        ]

    def __str__(self):
        return f"{self.user.phone} - {self.status} - {self.created_at}"


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
        ("NOTIFICATIONS", "Open Notification Center"),
    ]
    OFFER_SCOPE_CHOICES = [
        ("NONE", "Message Only"),
        ("RENT", "Rent"),
        ("PURCHASE", "Purchase"),
        ("SERVICE", "Service"),
        ("AMC", "AMC"),
        ("REFERRAL", "Referral"),
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
    offer_scope = models.CharField(max_length=12, choices=OFFER_SCOPE_CHOICES, default="NONE")
    auto_apply = models.BooleanField(default=False)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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


class NotificationCampaign(models.Model):
    CATEGORY_CHOICES = [
        ("GENERAL", "General"),
        ("HRMS", "HRMS"),
        ("ATTENDANCE", "Attendance"),
        ("LEAVE", "Leave"),
        ("PAYROLL", "Payroll"),
        ("JOB", "Job"),
        ("SERVICE", "Service"),
        ("COMPLAINT", "Complaint"),
        ("RENT", "Rent"),
        ("PAYMENT", "Payment"),
        ("OFFER", "Offer"),
        ("SECURITY", "Security"),
        ("SYSTEM", "System"),
    ]
    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("NORMAL", "Normal"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]
    AUDIENCE_CHOICES = [
        ("ALL", "Everyone"),
        ("CUSTOMERS", "All Customers"),
        ("EMPLOYEES", "All Employees"),
        ("ROLE", "Specific Role"),
        ("USERS", "Selected Users"),
    ]
    ACTION_CHOICES = CustomerEngagement.ACTION_CHOICES

    title = models.CharField(max_length=140)
    message = models.TextField(max_length=1000)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="GENERAL")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMAL")
    audience = models.CharField(max_length=16, choices=AUDIENCE_CHOICES, default="ALL")
    target_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, blank=True, default="")
    target_users = models.ManyToManyField(User, blank=True, related_name="notification_campaign_targets")
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default="NONE")
    action_label = models.CharField(max_length=50, blank=True, default="")
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_notification_campaigns",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class UserNotification(models.Model):
    campaign = models.ForeignKey(
        NotificationCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=140)
    message = models.TextField(max_length=1000)
    category = models.CharField(max_length=20, choices=NotificationCampaign.CATEGORY_CHOICES, default="GENERAL")
    priority = models.CharField(max_length=10, choices=NotificationCampaign.PRIORITY_CHOICES, default="NORMAL")
    action = models.CharField(max_length=16, choices=NotificationCampaign.ACTION_CHOICES, default="NONE")
    action_label = models.CharField(max_length=50, blank=True, default="")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"], name="acct_notif_user_read_idx"),
            models.Index(fields=["category", "created_at"], name="acct_notif_category_idx"),
        ]

    def __str__(self):
        return f"{self.user.phone}: {self.title}"


class OfferRedemption(models.Model):
    engagement = models.ForeignKey(
        CustomerEngagement,
        on_delete=models.PROTECT,
        related_name="redemptions",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offer_redemptions",
    )
    customer_phone = models.CharField(max_length=15, blank=True, default="")
    scope = models.CharField(max_length=12, choices=CustomerEngagement.OFFER_SCOPE_CHOICES)
    reference = models.CharField(max_length=80)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-redeemed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["engagement", "scope", "reference"],
                name="unique_offer_scope_reference_redemption",
            )
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
