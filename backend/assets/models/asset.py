from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import ROModel
from customers.models import Customer


class ROAsset(models.Model):

    STATUS_CHOICES = [
        ("WAREHOUSE", "Warehouse"),
        ("ASSIGNED", "Assigned"),
        ("INSTALLED", "Installed"),
        ("SERVICE", "Service"),
        ("REPAIR", "Repair"),
        ("RETURNED", "Returned"),
        ("REFURBISHED", "Refurbished"),
        ("SCRAP", "Scrap"),
    ]

    asset_id = models.CharField(
        max_length=25,
        unique=True,
        blank=True
    )

    ro_model = models.ForeignKey(
        ROModel,
        on_delete=models.PROTECT,
        related_name="assets"
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True
    )

    qr_code = models.CharField(
        max_length=200,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="WAREHOUSE"
    )

    current_customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ro_assets"
    )

    purchase_date = models.DateField(
        null=True,
        blank=True
    )

    next_filter_change_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional planned filter-change date used by RO Alarm Center.",
    )

    output_tds_attention_level = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Optional maintenance attention threshold. Crossing it creates an "
            "attention alarm; it is not a water-safety determination."
        ),
    )

    alarm_monitoring_enabled = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if not self.asset_id:

            year = timezone.now().year

            last = ROAsset.objects.order_by("-id").first()

            if last:
                try:
                    last_no = int(last.asset_id.split("-")[-1])
                except Exception:
                    last_no = 0
            else:
                last_no = 0

            self.asset_id = f"ARI-RO-{year}-{last_no+1:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.asset_id


class ROAlarm(models.Model):
    TYPE_CHOICES = [
        ("SERVICE_DUE", "Service Due"),
        ("FILTER_DUE", "Filter Change Due"),
        ("LEAKAGE", "Leakage"),
        ("NOISE", "Unusual Noise"),
        ("TASTE", "Taste Change"),
        ("TDS", "TDS Attention"),
        ("LOW_FLOW", "Low Water Flow"),
        ("OTHER", "Other"),
    ]
    SEVERITY_CHOICES = [
        ("LOW", "Low"),
        ("NORMAL", "Normal"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("ACKNOWLEDGED", "Acknowledged"),
        ("RESOLVED", "Resolved"),
    ]
    SOURCE_CHOICES = [
        ("SYSTEM", "System"),
        ("CUSTOMER", "Customer"),
        ("ENGINEER", "Engineer"),
        ("STAFF", "Staff"),
    ]

    ro_asset = models.ForeignKey(
        ROAsset,
        on_delete=models.CASCADE,
        related_name="alarms",
    )
    alarm_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default="NORMAL",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="OPEN",
        db_index=True,
    )
    source = models.CharField(
        max_length=12,
        choices=SOURCE_CHOICES,
        default="SYSTEM",
    )
    title = models.CharField(max_length=140)
    message = models.TextField(max_length=1000, blank=True, default="")
    observed_value = models.PositiveIntegerField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    dedupe_key = models.CharField(
        max_length=180,
        unique=True,
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ro_alarms",
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_ro_alarms",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_ro_alarms",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["ro_asset", "status", "alarm_type"],
                name="asset_alarm_state_idx",
            ),
            models.Index(
                fields=["status", "due_date"],
                name="asset_alarm_due_idx",
            ),
        ]

    def __str__(self):
        return f"{self.ro_asset.asset_id} • {self.get_alarm_type_display()}"
