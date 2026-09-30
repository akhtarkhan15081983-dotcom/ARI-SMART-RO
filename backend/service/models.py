from django.db import models, transaction
from django.utils import timezone

from customers.models import Customer
from employees.models import EmployeeProfile
from assets.models import ROAsset
from jobs.models import Job
from partmaster.models import PartMaster
from inventory.models import InventoryItem
from tenancy.id_allocator import acquire_allocator_lock, next_visible_number


class Service(models.Model):
    SERVICE_TYPES = [
        ("REGULAR", "Regular Service"),
        ("COMPLAINT", "Complaint Service"),
        ("AMC", "AMC Service"),
        ("PAID", "Paid Service"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    service_id = models.CharField(max_length=25, unique=True, blank=True)
    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="services",
        db_index=True,
    )
    job = models.OneToOneField(
        Job, on_delete=models.PROTECT, related_name="service", null=True, blank=True,
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="services")
    engineer = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name="services")
    ro_asset = models.ForeignKey(ROAsset, on_delete=models.PROTECT, related_name="services")
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, default="REGULAR")
    scheduled_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)
    input_tds = models.PositiveIntegerField(null=True, blank=True)
    output_tds = models.PositiveIntegerField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    remarks = models.TextField(blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.service_id:
            return super().save(*args, **kwargs)

        year = timezone.now().year
        with transaction.atomic():
            acquire_allocator_lock(f"service:{year}")
            number = next_visible_number(Service, "service_id", "SER", year)
            self.service_id = f"SER-{year}-{number:06d}"
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.service_id


class ServicePart(models.Model):
    ACTION_USED = "USED"
    ACTION_REPLACED = "REPLACED"
    ACTION_CLEANED = "CLEANED"
    ACTION_INSPECTED = "INSPECTED"
    ACTION_CHOICES = [
        (ACTION_USED, "Part Used"),
        (ACTION_REPLACED, "Part Replaced"),
        (ACTION_CLEANED, "Part Cleaned"),
        (ACTION_INSPECTED, "Part Inspected"),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="parts_used")
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    remarks = models.CharField(max_length=200, blank=True)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default=ACTION_USED)
    verification_method = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return f"{self.service.service_id} - {self.part.name}"


class ServicePhoto(models.Model):
    PHOTO_TYPES = [("BEFORE", "Before Service"), ("AFTER", "After Service")]
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="photos")
    photo = models.ImageField(upload_to="service/photos/")
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.service.service_id


class ServiceSignature(models.Model):
    service = models.OneToOneField(Service, on_delete=models.CASCADE, related_name="signature")
    signature = models.ImageField(upload_to="service/signatures/")
    customer_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.service.service_id


class ServiceIntervalPolicy(models.Model):
    """Admin-configurable preventive interval for one part/model/configuration.

    No universal replacement interval is assumed. A health countdown exists
    only when an active policy is configured for the tenant and part.
    """

    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.CASCADE,
        related_name="ro_service_interval_policies",
    )
    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT,
        related_name="service_interval_policies",
    )
    ro_model = models.ForeignKey(
        "products.ROModel",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="service_interval_policies",
    )
    configuration_key = models.CharField(max_length=80, blank=True, default="")
    interval_days = models.PositiveIntegerField()
    due_soon_days = models.PositiveIntegerField(default=30)
    reminder_days = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "part", "ro_model", "configuration_key"],
                name="uniq_ro_service_interval_policy",
            ),
        ]
        ordering = ["part__name", "ro_model__model_name", "configuration_key"]

    def __str__(self):
        model = self.ro_model.model_name if self.ro_model_id else "Any model"
        return f"{self.part.name} / {model} / {self.interval_days} days"


class PartServiceCycleAudit(models.Model):
    """Immutable evidence that an explicit verified replacement started a new cycle.

    The actual replacement remains ServicePart. This table is an audit/calculation
    trail only; it never replaces or deletes service/replacement history.
    """

    source_service_part = models.OneToOneField(
        ServicePart,
        on_delete=models.PROTECT,
        related_name="cycle_audit",
    )
    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.PROTECT,
        related_name="part_service_cycle_audits",
    )
    ro_asset = models.ForeignKey(
        ROAsset,
        on_delete=models.PROTECT,
        related_name="part_service_cycle_audits",
    )
    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT,
        related_name="service_cycle_audits",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="part_cycle_audits",
    )
    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="part_service_cycle_audits",
    )
    cycle_started_at = models.DateTimeField()
    old_due_date = models.DateField(null=True, blank=True)
    new_due_date = models.DateField(null=True, blank=True)
    verification_method = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cycle_started_at", "-id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Part service-cycle audit records are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Part service-cycle audit records are immutable.")

    def __str__(self):
        return f"{self.ro_asset.asset_id} / {self.part.name} / {self.cycle_started_at:%Y-%m-%d}"
