from django.db import models

from customers.models import Customer
from employees.models import EmployeeProfile
from assets.models import ROAsset
from random import randint


class Job(models.Model):

    JOB_TYPES = [
        ("INSTALLATION", "Installation"),
        ("SERVICE", "Service"),
        ("COMPLAINT", "Complaint"),
        ("PAYMENT", "Payment Collection"),
        ("REMOVAL", "Machine Removal"),
    ]

    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]

    STATUS_CHOICES = [
        ("ASSIGNED", "Assigned"),
        ("ACCEPTED", "Accepted"),
        ("ON_THE_WAY", "On The Way"),
        ("ARRIVED", "Arrived"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    job_id = models.CharField(
        max_length=25,
        unique=True,
        blank=True,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="jobs"
    )

    ro_asset = models.ForeignKey(
        ROAsset,
        on_delete=models.PROTECT,
        related_name="jobs"
    )

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="jobs"
    )

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPES,
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="MEDIUM",
    )

    scheduled_date = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ASSIGNED",
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    on_the_way_at = models.DateTimeField(
        null=True,
        blank=True
    )

    arrived_at = models.DateTimeField(
        null=True,
        blank=True
    )
    customer_otp = models.CharField(
        max_length=6,
        blank=True,
        null=True,
    )

    otp_verified = models.BooleanField(
        default=False,
    )

    otp_created_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    otp_attempts = models.PositiveIntegerField(
        default=0,
    )

    in_progress_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def save(self, *args, **kwargs):
        from django.utils import timezone

        if not self.job_id:
            year = timezone.now().year

            last_job = Job.objects.filter(
                job_id__startswith=f"JOB-{year}"
            ).order_by("id").last()

            if last_job:
                last_number = int(last_job.job_id.split("-")[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.job_id = f"JOB-{year}-{new_number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.job_id or f"Job {self.pk}"

class JobGPSLog(models.Model):

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="gps_logs"
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7
    )

    accuracy = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    captured_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-captured_at"]

    def __str__(self):
        return f"{self.job.job_id} - {self.captured_at}"

class JobMedia(models.Model):

    MEDIA_TYPES = [
        ("PHOTO", "Photo"),
        ("VIDEO", "Video"),
    ]

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="media"
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPES,
    )

    file = models.FileField(
        upload_to="jobs/media/"
    )

    description = models.CharField(
        max_length=100,
        blank=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.job.job_id} - {self.media_type}"

class JobActivityLog(models.Model):

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT
    )

    activity = models.CharField(
        max_length=100
    )

    remarks = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.job.job_id} - {self.activity}"

class JobPartUsed(models.Model):

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="parts_used"
    )

    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="job_usage"
    )

    quantity = models.PositiveIntegerField(default=1)

    remarks = models.CharField(
        max_length=200,
        blank=True
    )

    used_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-used_at"]

    def __str__(self):
        return f"{self.job.job_id} - {self.inventory_item}"

class JobSignature(models.Model):

    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="signature"
    )

    signature = models.ImageField(
        upload_to="jobs/signatures/"
    )

    customer_name = models.CharField(
        max_length=100
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.job.job_id

