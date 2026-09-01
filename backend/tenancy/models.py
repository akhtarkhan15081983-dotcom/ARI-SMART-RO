from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    INTERVAL_CHOICES = [("MONTHLY", "Monthly"), ("ANNUAL", "Annual")]

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=240, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    billing_interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, default="MONTHLY")
    employee_limit = models.PositiveIntegerField(default=5)
    customer_limit = models.PositiveIntegerField(default=250)
    branch_limit = models.PositiveIntegerField(default=1)
    features = models.JSONField(default=list, blank=True)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price"]

    def __str__(self):
        return self.name


class Company(models.Model):
    LIFECYCLE_CHOICES = [
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("DEACTIVATED", "Deactivated"),
        ("ARCHIVED", "Archived"),
        ("PENDING_DELETION", "Pending deletion"),
    ]
    name = models.CharField(max_length=150)
    legal_name = models.CharField(max_length=180, blank=True)
    slug = models.SlugField(max_length=80, unique=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    logo = models.ImageField(upload_to="companies/logos/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#075985")
    secondary_color = models.CharField(max_length=7, default="#0891B2")
    support_phone = models.CharField(max_length=15, blank=True)
    support_email = models.EmailField(blank=True)
    app_display_name = models.CharField(max_length=80, blank=True)
    tagline = models.CharField(max_length=140, blank=True)
    welcome_message = models.CharField(max_length=280, blank=True)
    show_public_shop = models.BooleanField(default=False)
    enabled_modules = models.JSONField(
        default=list,
        blank=True,
        help_text="Public/customer module codes enabled for this tenant.",
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    timezone = models.CharField(max_length=50, default="Asia/Kolkata")
    is_active = models.BooleanField(default=True)
    lifecycle_status = models.CharField(max_length=20, choices=LIFECYCLE_CHOICES, default="ACTIVE")
    lifecycle_reason = models.CharField(max_length=500, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    deletion_scheduled_for = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return self.app_display_name or self.name


class CompanyLifecycleEvent(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="lifecycle_events"
    )
    company_name = models.CharField(max_length=150)
    company_slug = models.SlugField(max_length=80)
    action = models.CharField(max_length=30)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    reason = models.CharField(max_length=500)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="company_lifecycle_actions",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_slug}: {self.action}"


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_head_office = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_company_branch_code"),
        ]
        ordering = ["company", "name"]

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class CompanyMembership(models.Model):
    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Company Admin"),
        ("MANAGER", "Manager"),
        ("STAFF", "Staff"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_memberships")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="memberships")
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "user"], name="unique_company_user_membership"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.company} ({self.role})"


class CompanySubscription(models.Model):
    STATUS_CHOICES = [
        ("TRIAL", "Trial"),
        ("ACTIVE", "Active"),
        ("PAST_DUE", "Past Due"),
        ("PAUSED", "Paused"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="TRIAL")
    starts_at = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    external_customer_id = models.CharField(max_length=120, blank=True)
    external_subscription_id = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def has_access(self):
        return self.status in {"TRIAL", "ACTIVE"} and self.current_period_end > timezone.now()

    def __str__(self):
        return f"{self.company} - {self.plan} ({self.status})"
