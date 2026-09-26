from django.conf import settings
from django.db import models


class ROPartsInspection(models.Model):
    INSPECTION_TYPES = [
        ("BASELINE", "Baseline scan"),
        ("VISUAL_CHECK", "Visual check"),
        ("REPLACEMENT", "Replacement"),
    ]
    SOURCES = [
        ("PHOTO_AI", "Photo + AI"),
        ("INVENTORY_JOB", "Inventory job"),
        ("MANUAL", "Manual confirmation"),
    ]
    STATUSES = [
        ("CAPTURED", "Captured"),
        ("ANALYZED", "Analyzed"),
        ("NEEDS_REVIEW", "Needs review"),
        ("CONFIRMED", "Confirmed"),
    ]

    ro_asset = models.ForeignKey(
        "assets.ROAsset",
        on_delete=models.CASCADE,
        related_name="parts_inspections",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="ro_parts_inspections",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ro_parts_inspections",
    )
    engineer = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ro_parts_inspections",
    )
    inspection_type = models.CharField(
        max_length=20,
        choices=INSPECTION_TYPES,
        default="VISUAL_CHECK",
    )
    source = models.CharField(max_length=20, choices=SOURCES, default="PHOTO_AI")
    status = models.CharField(max_length=20, choices=STATUSES, default="CAPTURED")
    captured_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    ai_provider = models.CharField(max_length=40, blank=True, default="")
    ai_model = models.CharField(max_length=80, blank=True, default="")
    ai_summary = models.TextField(blank=True, default="")
    raw_ai_result = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ro_parts_inspections",
    )

    class Meta:
        ordering = ["-captured_at", "-id"]
        indexes = [
            models.Index(fields=["ro_asset", "captured_at"], name="jobs_ro_parts_asset_dt_idx"),
            models.Index(fields=["customer", "captured_at"], name="jobs_ro_parts_customer_dt_idx"),
        ]

    def __str__(self):
        return f"{self.ro_asset_id}:{self.inspection_type}:{self.captured_at:%Y-%m-%d}"


class ROPartsInspectionPhoto(models.Model):
    inspection = models.ForeignKey(
        ROPartsInspection,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to="jobs/ro_parts_passport/%Y/%m/")
    angle = models.CharField(max_length=30, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Inspection {self.inspection_id} photo {self.id}"


class ROPartsObservation(models.Model):
    DATE_SOURCES = [
        ("BASELINE_ASSUMED", "Baseline date (actual prior replacement unknown)"),
        ("CARRIED_FORWARD", "Carried from previous confirmed record"),
        ("REPLACEMENT_CONFIRMED", "Replacement confirmed by employee"),
        ("INVENTORY_JOB", "Replacement verified from inventory job"),
    ]

    inspection = models.ForeignKey(
        ROPartsInspection,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    part_key = models.CharField(max_length=60)
    part_name = models.CharField(max_length=120)
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    visible = models.BooleanField(default=True)
    confirmed = models.BooleanField(default=False)
    installed_on = models.DateField(null=True, blank=True)
    date_source = models.CharField(
        max_length=30,
        choices=DATE_SOURCES,
        blank=True,
        default="",
    )
    evidence_notes = models.CharField(max_length=250, blank=True, default="")

    class Meta:
        ordering = ["part_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["inspection", "part_key"],
                name="unique_ro_part_per_inspection",
            )
        ]
        indexes = [
            models.Index(fields=["part_key", "confirmed"], name="jobs_ro_part_key_conf_idx"),
        ]

    def __str__(self):
        return f"{self.inspection_id}:{self.part_key}"
