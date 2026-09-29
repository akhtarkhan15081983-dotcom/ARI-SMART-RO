from django.db import models, transaction
from django.utils import timezone

from customers.models import Customer
from employees.models import EmployeeProfile
from service.models import Service
from tenancy.id_allocator import acquire_allocator_lock, next_visible_number


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

    complaint_id = models.CharField(max_length=30, unique=True, blank=True)
    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="complaints",
        db_index=True,
    )
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="complaints")
    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="complaints",
        null=True,
        blank=True,
    )
    complaint_type = models.CharField(max_length=30, choices=COMPLAINT_TYPE_CHOICES, default="OTHER")
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default="NORMAL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    complaint_date = models.DateTimeField(default=timezone.now)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    engineer_remarks = models.TextField(blank=True)
    resolution = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
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
        if self.status == "RESOLVED" and self.resolved_date is None:
            self.resolved_date = timezone.now()
        if self.status not in ["RESOLVED", "CLOSED"]:
            self.resolved_date = None

        if self.complaint_id:
            return super().save(*args, **kwargs)

        year = timezone.now().year
        with transaction.atomic():
            acquire_allocator_lock(f"complaint:{year}")
            number = next_visible_number(Complaint, "complaint_id", "CMP", year)
            self.complaint_id = f"CMP-{year}-{number:06d}"
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.complaint_id
