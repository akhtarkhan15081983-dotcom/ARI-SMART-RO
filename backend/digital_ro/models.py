from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class DigitalROPassport(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("NEEDS_REVIEW", "Needs Review"),
        ("ARCHIVED", "Archived"),
    ]

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="digital_ro_passport",
    )
    ro_asset = models.ForeignKey(
        "assets.ROAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="digital_passports",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    hero_photo = models.ImageField(upload_to="digital_ro/hero/", blank=True)
    tracking_started_at = models.DateTimeField(default=timezone.now)
    last_scan_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="digital_ro_passports_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Digital RO - {self.customer.customer_id}"


class DigitalROPhoto(models.Model):
    VIEW_CHOICES = [
        ("FRONT", "Front"),
        ("INTERNAL_LEFT", "Internal Left"),
        ("INTERNAL_RIGHT", "Internal Right"),
        ("INTERNAL_CLOSE", "Internal Close-up"),
        ("PART_EVIDENCE", "Part Evidence"),
    ]

    passport = models.ForeignKey(
        DigitalROPassport,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    view_type = models.CharField(max_length=30, choices=VIEW_CHOICES)
    image = models.ImageField(upload_to="digital_ro/scans/")
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="digital_ro_photos",
    )
    captured_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["captured_at", "id"]


class DigitalROPart(models.Model):
    PART_CHOICES = [
        ("SEDIMENT", "Sediment Filter"),
        ("PRE_CARBON", "Pre Carbon Filter"),
        ("RO_MEMBRANE", "RO Membrane"),
        ("POST_CARBON", "Post Carbon"),
        ("ALKALINE", "Alkaline Cartridge"),
        ("COPPER", "Copper Cartridge"),
        ("PUMP", "Booster Pump"),
        ("SV", "Solenoid Valve"),
        ("SMPS", "SMPS / Power Unit"),
        ("UV", "UV Chamber"),
        ("OTHER", "Other"),
    ]
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("REPLACED", "Replaced"),
        ("REMOVED", "Removed"),
        ("NEEDS_REVIEW", "Needs Review"),
    ]

    passport = models.ForeignKey(
        DigitalROPassport,
        on_delete=models.CASCADE,
        related_name="parts",
    )
    part_type = models.CharField(max_length=30, choices=PART_CHOICES)
    display_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    tracking_started_at = models.DateTimeField(default=timezone.now)
    last_replaced_at = models.DateTimeField(null=True, blank=True)
    hotspot_x = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    hotspot_y = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    ai_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    employee_confirmed = models.BooleanField(default=False)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="digital_ro_parts_confirmed",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["passport", "part_type"],
                name="unique_current_digital_ro_part_type",
            )
        ]
        ordering = ["part_type", "id"]

    @property
    def label(self):
        return self.display_name.strip() or self.get_part_type_display()


class DigitalROPartEvent(models.Model):
    EVENT_CHOICES = [
        ("TRACKED", "Tracking Started"),
        ("INSPECTED", "Inspected"),
        ("INSTALLED", "Installed"),
        ("REPLACED", "Replaced"),
        ("REMOVED", "Removed"),
        ("CORRECTED", "Corrected"),
    ]

    part = models.ForeignKey(
        DigitalROPart,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    event_at = models.DateTimeField(default=timezone.now)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="digital_ro_part_events",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="digital_ro_part_events",
    )
    before_photo = models.ImageField(upload_to="digital_ro/evidence/before/", blank=True)
    after_photo = models.ImageField(upload_to="digital_ro/evidence/after/", blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=30, default="EMPLOYEE_CONFIRMATION")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_at", "-id"]
