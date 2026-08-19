from django.db import models
from django.utils import timezone

from customers.models import Customer
from employees.models import EmployeeProfile
from assets.models import ROAsset
from jobs.models import Job
from partmaster.models import PartMaster
from inventory.models import InventoryItem


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

    service_id = models.CharField(
        max_length=25,
        unique=True,
        blank=True,
    )

    job = models.OneToOneField(
        Job,
        on_delete=models.PROTECT,
        related_name="service",
        null=True,
        blank=True,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="services",
    )

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="services",
    )

    ro_asset = models.ForeignKey(
        ROAsset,
        on_delete=models.PROTECT,
        related_name="services",
    )

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPES,
        default="REGULAR",
    )

    scheduled_date = models.DateTimeField()

    completed_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    input_tds = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    output_tds = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    remarks = models.TextField(blank=True)

    next_service_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.service_id:

            year = timezone.now().year

            last = Service.objects.filter(
                service_id__startswith=f"SER-{year}"
            ).order_by("id").last()

            if last:
                number = int(last.service_id.split("-")[-1]) + 1
            else:
                number = 1

            self.service_id = f"SER-{year}-{number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.service_id

class ServicePart(models.Model):

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="parts_used",
    )

    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT,
    )

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    quantity = models.PositiveIntegerField(default=1)

    remarks = models.CharField(
        max_length=200,
        blank=True,
    )

    def __str__(self):
        return f"{self.service.service_id} - {self.part.name}"

class ServicePhoto(models.Model):

    PHOTO_TYPES = [
        ("BEFORE", "Before Service"),
        ("AFTER", "After Service"),
    ]

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="photos",
    )

    photo = models.ImageField(
        upload_to="service/photos/",
    )

    photo_type = models.CharField(
        max_length=20,
        choices=PHOTO_TYPES,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.service.service_id

class ServiceSignature(models.Model):

    service = models.OneToOneField(
        Service,
        on_delete=models.CASCADE,
        related_name="signature",
    )

    signature = models.ImageField(
        upload_to="service/signatures/",
    )

    customer_name = models.CharField(
        max_length=100,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.service.service_id


