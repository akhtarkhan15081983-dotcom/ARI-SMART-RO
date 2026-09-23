from calendar import monthrange
from datetime import date, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import ROModel
from customers.models import Customer


def _add_months(value, months):
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


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
    DEPLOYMENT_CHOICES = [("", "Unassigned"), ("SALE", "Sale"), ("RENT", "Rental")]
    QC_STATUS_CHOICES = [("PENDING", "QC Pending"), ("PASSED", "QC Passed"), ("FAILED", "QC Failed")]

    asset_id = models.CharField(max_length=25, unique=True, blank=True)
    ro_model = models.ForeignKey(ROModel, on_delete=models.PROTECT, related_name="assets")
    serial_number = models.CharField(max_length=100, unique=True, blank=True)
    qr_code = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="WAREHOUSE")
    deployment_type = models.CharField(max_length=10, choices=DEPLOYMENT_CHOICES, blank=True, default="")
    current_customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="ro_assets")
    purchase_date = models.DateField(null=True, blank=True)
    purchase_invoice = models.CharField(max_length=100, blank=True, default="")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    assigned_at = models.DateTimeField(null=True, blank=True)
    qc_status = models.CharField(max_length=10, choices=QC_STATUS_CHOICES, default="PENDING")
    qc_checked_at = models.DateTimeField(null=True, blank=True)
    qc_checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="qc_checked_ro_assets")
    qc_notes = models.TextField(blank=True, default="")
    cleaned_at = models.DateTimeField(null=True, blank=True)
    sanitized_at = models.DateTimeField(null=True, blank=True)
    reserved_for_customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="reserved_ro_assets")
    reserved_at = models.DateTimeField(null=True, blank=True)
    reservation_expires_at = models.DateTimeField(null=True, blank=True)
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
            self.asset_id = f"ARI-RO-{year}-{last_no + 1:06d}"
        super().save(*args, **kwargs)

    @property
    def reservation_active(self):
        return self.reserved_for_customer_id is not None and (
            self.reservation_expires_at is None or self.reservation_expires_at > timezone.now()
        )

    @property
    def bom_verified(self):
        active = self.components.filter(status="ACTIVE")
        return active.exists() and not active.filter(scan_status="PENDING").exists()

    @property
    def release_ready(self):
        return self.is_active and self.status == "WAREHOUSE" and self.qc_status == "PASSED" and self.bom_verified and not self.reservation_active

    def __str__(self):
        return self.asset_id


class ROAssetMovement(models.Model):
    ACTION_CHOICES = [
        ("RECEIVED", "Received into warehouse"), ("QC_PASSED", "QC Passed"),
        ("QC_FAILED", "QC Failed"), ("RESERVED", "Reserved"),
        ("RESERVATION_RELEASED", "Reservation Released"), ("SALE_ALLOCATED", "Allocated for sale"),
        ("RENT_ALLOCATED", "Allocated for rental"), ("INSTALLED", "Installed"),
        ("RENT_RETURNED", "Rental returned"), ("RESTOCKED", "Returned to warehouse"),
        ("REPAIR", "Sent to repair"), ("SCRAP", "Scrapped"), ("STATUS_CHANGE", "Status changed"),
    ]
    asset = models.ForeignKey(ROAsset, on_delete=models.PROTECT, related_name="movements")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="ro_asset_movements")
    request_id = models.PositiveBigIntegerField(null=True, blank=True)
    request_number = models.CharField(max_length=30, blank=True, default="")
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20, blank=True, default="")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="ro_asset_movements")
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.asset.asset_id} - {self.action}"


class ROAssetComponent(models.Model):
    STATUS_CHOICES = [("ACTIVE", "Active / Installed"), ("REPLACED", "Replaced"), ("REMOVED", "Removed")]
    SOURCE_CHOICES = [("FACTORY_BOM", "Factory / Model BOM"), ("INSTALLATION", "Installation"), ("SERVICE", "Service Replacement"), ("MANUAL", "Manual Correction")]
    SCAN_STATUS_CHOICES = [("NOT_REQUIRED", "Scan not required"), ("PENDING", "Scan / serial verification pending"), ("VERIFIED", "Serial / QR verified")]
    asset = models.ForeignKey(ROAsset, on_delete=models.CASCADE, related_name="components")
    part = models.ForeignKey("partmaster.PartMaster", on_delete=models.PROTECT, related_name="ro_asset_components")
    inventory_item = models.OneToOneField("inventory.InventoryItem", on_delete=models.PROTECT, null=True, blank=True, related_name="ro_asset_component")
    quantity = models.PositiveIntegerField(default=1)
    serial_number = models.CharField(max_length=100, blank=True, default="", db_index=True)
    batch_number = models.CharField(max_length=100, blank=True, default="")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="FACTORY_BOM")
    source_reference = models.CharField(max_length=80, blank=True, default="", db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    scan_status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default="NOT_REQUIRED")
    installed_at = models.DateTimeField(default=timezone.now)
    removed_at = models.DateTimeField(null=True, blank=True)
    installed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="installed_ro_components")
    notes = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["part__name", "id"]
        indexes = [models.Index(fields=["asset", "status"]), models.Index(fields=["asset", "scan_status"])]

    @property
    def warranty_end_date(self):
        months = int(self.part.warranty_months or 0)
        return _add_months(self.installed_at.date(), months) if months > 0 else None

    @property
    def replacement_due_date(self):
        days = int(getattr(self.part, "replacement_interval_days", 0) or 0)
        return self.installed_at.date() + timedelta(days=days) if days > 0 else None

    def __str__(self):
        return f"{self.asset.asset_id} - {self.part.code} - {self.status}"


class ROAssetComponentEvent(models.Model):
    ACTION_CHOICES = [("CREATED", "Component created"), ("SCAN_VERIFIED", "Serial / QR verified"), ("INSTALLATION_VERIFIED", "Verified at installation"), ("REPLACED", "Component replaced"), ("REMOVED", "Component removed"), ("QUANTITY_CHANGED", "Quantity changed"), ("NOTE", "Note")]
    asset = models.ForeignKey(ROAsset, on_delete=models.CASCADE, related_name="component_events")
    component = models.ForeignKey(ROAssetComponent, on_delete=models.PROTECT, related_name="events")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    part = models.ForeignKey("partmaster.PartMaster", on_delete=models.PROTECT, related_name="ro_component_events")
    quantity = models.PositiveIntegerField(default=1)
    serial_number = models.CharField(max_length=100, blank=True, default="")
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20, blank=True, default="")
    source_reference = models.CharField(max_length=80, blank=True, default="", db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="ro_component_events")
    remarks = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.asset.asset_id} - {self.part.code} - {self.action}"


class ROStockAudit(models.Model):
    STATUS_CHOICES = [("OPEN", "Open"), ("COMPLETED", "Completed")]
    reference = models.CharField(max_length=30, unique=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN")
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="started_ro_stock_audits")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"RO-AUD-{timezone.now():%Y%m%d}-{ROStockAudit.objects.count() + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class ROStockAuditItem(models.Model):
    audit = models.ForeignKey(ROStockAudit, on_delete=models.CASCADE, related_name="items")
    asset = models.ForeignKey(ROAsset, on_delete=models.PROTECT, related_name="stock_audit_items")
    expected_status = models.CharField(max_length=20)
    physically_found = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(null=True, blank=True)
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="scanned_ro_stock_audit_items")
    remarks = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        unique_together = ("audit", "asset")

    def __str__(self):
        return f"{self.audit.reference} - {self.asset.asset_id}"
