from django.db import models
from django.utils import timezone

from customers.models import Customer
from employees.models import EmployeeProfile
from service.models import Service


class Complaint(models.Model):

    PRIORITY_CHOICES = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
        ("EMERGENCY", "Emergency"),
    ]

    STATUS_CHOICES = [
        ("NEW", "New"),
        ("ASSIGNED", "Assigned"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    ]

    COMPLAINT_TYPE_CHOICES = [
        ("RO_NOT_WORKING", "RO Not Working"),
        ("WATER_LEAKAGE", "Water Leakage"),
        ("LOW_TDS", "Low TDS"),
        ("BAD_TASTE", "Bad Taste"),
        ("LOW_WATER_FLOW", "Low Water Flow"),
        ("NO_WATER", "No Water"),
        ("PUMP_PROBLEM", "Pump Problem"),
        ("MEMBRANE_PROBLEM", "Membrane Problem"),
        ("FILTER_PROBLEM", "Filter Problem"),
        ("ELECTRICAL", "Electrical Problem"),
        ("NOISE", "Unusual Noise"),
        ("AMC_SERVICE", "AMC Service"),
        ("OTHER", "Other"),
    ]

    complaint_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="complaints",
    )

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="complaints",
        null=True,
        blank=True,
    )

    complaint_type = models.CharField(
        max_length=30,
        choices=COMPLAINT_TYPE_CHOICES,
        default="OTHER",
    )

    description = models.TextField(blank=True)

    priority = models.CharField(
        max_length=15,
        choices=PRIORITY_CHOICES,
        default="NORMAL",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="NEW",
    )

    complaint_date = models.DateTimeField(default=timezone.now)

    scheduled_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    engineer_remarks = models.TextField(blank=True)
    resolution = models.TextField(blank=True)

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

    linked_service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="complaints",
        null=True,
        blank=True,
    )

    job = models.OneToOneField(
        "jobs.Job",
        on_delete=models.SET_NULL,
        related_name="complaint_source",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.complaint_id:
            year = timezone.now().year
            last = (
                Complaint.objects
                .filter(complaint_id__startswith=f"CMP-{year}")
                .order_by("id")
                .last()
            )
            if last:
                try:
                    number = int(last.complaint_id.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    number = 1
            else:
                number = 1
            self.complaint_id = f"CMP-{year}-{number:06d}"

        if self.status == "RESOLVED" and self.resolved_date is None:
            self.resolved_date = timezone.now()

        if self.status not in ["RESOLVED", "CLOSED"]:
            self.resolved_date = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.complaint_id
