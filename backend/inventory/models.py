from django.conf import settings
from django.db import models
from django.utils import timezone

from partmaster.models import PartMaster
from purchase.models import PurchaseItem
from employees.models import EmployeeProfile

import qrcode
from io import BytesIO
from django.core.files import File


class InventoryItem(models.Model):
    STATUS_CHOICES = [
        ("PENDING_RECEIPT", "Pending Receipt"),
        ("IN_STOCK", "In Stock"),
        ("ISSUED", "Issued To Engineer"),
        ("INSTALLED", "Installed"),
        ("RETURNED", "Returned"),
        ("SCRAP", "Scrap"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING_RECEIPT")
    purchase_item = models.ForeignKey(PurchaseItem, on_delete=models.PROTECT, related_name="inventory_items")
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT)
    serial_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    barcode = models.CharField(max_length=100, blank=True)
    manufacturing_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="received_inventory_items",
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.serial_number and not self.qr_code:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(self.serial_number)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            filename = f"{self.serial_number}.png"
            self.qr_code.save(filename, File(buffer), save=False)
            super().save(update_fields=["qr_code"])

    def __str__(self):
        return self.serial_number or f"Inventory #{self.id}"


class EngineerBagItem(models.Model):
    STATUS_CHOICES = [("ISSUED", "Issued"), ("INSTALLED", "Installed"), ("RETURNED", "Returned")]
    engineer = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="bag_items")
    inventory_item = models.OneToOneField(InventoryItem, on_delete=models.CASCADE, related_name="bag_item")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ISSUED")
    issue_date = models.DateTimeField(auto_now_add=True)
    install_date = models.DateTimeField(blank=True, null=True)
    return_date = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.engineer.employee_id} - {self.inventory_item.serial_number}"


class InventoryAuditLog(models.Model):
    ACTION_CHOICES = [
        ("ISSUED", "Issued To Engineer"), ("INSTALLED", "Installed"),
        ("RETURNED", "Returned"), ("SCRAP", "Marked Scrap"),
        ("STATUS_CHANGE", "Status Changed"), ("SECURITY_REJECT", "Security Rejection"),
        ("RECEIVED", "Received Into Stock"),
    ]
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="audit_logs")
    engineer = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_audit_logs")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_audit_logs")
    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, null=True, blank=True, related_name="inventory_audit_logs")
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    serial_number = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.inventory_item} - {self.action} - {self.created_at}"


class PartRequest(models.Model):
    STATUS_CHOICES = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("FULFILLED", "Fulfilled")]
    engineer = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="part_requests")
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, related_name="engineer_requests")
    quantity = models.PositiveIntegerField(default=1)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_part_requests")
    review_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.engineer.employee_id} - {self.part.code} x {self.quantity}"


class PartRequestEvent(models.Model):
    ACTION_CHOICES = [("CREATED", "Created"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("FULFILLED", "Fulfilled")]
    part_request = models.ForeignKey(PartRequest, on_delete=models.CASCADE, related_name="events")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="part_request_actions")
    remarks = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PartStockAudit(models.Model):
    STATUS_CHOICES = [("OPEN", "Open"), ("COMPLETED", "Completed")]
    reference = models.CharField(max_length=32, unique=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN")
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="started_part_stock_audits")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PART-AUD-{timezone.now():%Y%m%d}-{PartStockAudit.objects.count() + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class PartStockAuditLine(models.Model):
    audit = models.ForeignKey(PartStockAudit, on_delete=models.CASCADE, related_name="lines")
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, related_name="stock_audit_lines")
    is_serialized = models.BooleanField(default=False)
    expected_quantity = models.PositiveIntegerField(default=0)
    counted_quantity = models.PositiveIntegerField(default=0)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="verified_part_stock_audit_lines")
    verified_at = models.DateTimeField(null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        unique_together = ("audit", "part")
        ordering = ["part__name"]

    @property
    def difference(self):
        return self.counted_quantity - self.expected_quantity

    def __str__(self):
        return f"{self.audit.reference} - {self.part.code}"


class PartStockAuditScan(models.Model):
    audit_line = models.ForeignKey(PartStockAuditLine, on_delete=models.CASCADE, related_name="scans")
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="physical_audit_scans")
    scanned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="part_stock_audit_scans")
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("audit_line", "inventory_item")

    def __str__(self):
        return f"{self.audit_line} - {self.inventory_item_id}"
