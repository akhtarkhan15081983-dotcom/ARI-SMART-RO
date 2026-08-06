from django.db import models
from customers.models import Customer
from employees.models import EmployeeProfile
from assets.models import ROAsset
from partmaster.models import PartMaster
from jobs.models import Job
from inventory.models import InventoryItem


class Installation(models.Model):

    BUSINESS_TYPES = [
        ("RENT", "Rental"),
        ("SALE", "Sale"),
        ("AMC", "AMC"),
    ]

    STATUS_CHOICES = [
        ("SCHEDULED", "Scheduled"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    installation_id = models.CharField(
        max_length=25,
        unique=True,
        blank=True,
    )

    job = models.OneToOneField(
        Job,
        on_delete=models.PROTECT,
        related_name="installation",
        null=True,
        blank=True,
    )
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="installations"
    )

    ro_asset = models.ForeignKey(
        ROAsset,
        on_delete=models.PROTECT,
        related_name="installations"
    )

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="installations"
    )

    business_type = models.CharField(
        max_length=10,
        choices=BUSINESS_TYPES,
        default="RENT",
    )

    scheduled_date = models.DateTimeField()

    completed_date = models.DateTimeField(
        null=True,
        blank=True
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

    referral_name = models.CharField(
        max_length=150,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SCHEDULED"
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.installation_id or f"Installation {self.pk}"

    def save(self, *args, **kwargs):
        from django.utils import timezone

        if not self.installation_id:
            year = timezone.now().year

            last = Installation.objects.filter(
                installation_id__startswith=f"INS-{year}"
            ).order_by("id").last()

            if last:
                last_number = int(last.installation_id.split("-")[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.installation_id = f"INS-{year}-{new_number:06d}"

        super().save(*args, **kwargs) 

        @property
        def job_customer(self):
            return self.job.customer if self.job else self.customer


        @property
        def job_engineer(self):
            return self.job.engineer if self.job else self.engineer


        @property
        def job_ro_asset(self):
            return self.job.ro_asset if self.job else self.ro_asset
        
    
# ==========================
# DEPRECATED
# Use jobs.JobMedia instead.
# Will be removed after data migration.
# ==========================
class InstallationPhoto(models.Model):
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name="photos"
    )

    photo = models.ImageField(upload_to="installation/photos/")

    photo_type = models.CharField(
        max_length=50,
        help_text="Front, Side, Customer, Water Source, etc."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.installation} - {self.photo_type}" 

# ==========================
# DEPRECATED
# Use jobs.JobMedia instead.
# Will be removed after data migration.
# ==========================
class InstallationVideo(models.Model):
    installation = models.OneToOneField(
        Installation,
        on_delete=models.CASCADE,
        related_name="video"
    )

    video = models.FileField(upload_to="installation/videos/")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.installation)

# ==========================
# DEPRECATED
# Use jobs.JobMedia instead.
# Will be removed after data migration.
# ==========================
class InstallationSignature(models.Model):
    installation = models.OneToOneField(
        Installation,
        on_delete=models.CASCADE,
        related_name="signature"
    )

    signature = models.ImageField(
        upload_to="installation/signatures/"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.installation)

class InstallationPart(models.Model):
    installation = models.ForeignKey(
        Installation,
        on_delete=models.CASCADE,
        related_name="installed_parts"
    )

    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT
    )

    serial_number = models.CharField(
        max_length=100,
        blank=True
    )

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.part.name  