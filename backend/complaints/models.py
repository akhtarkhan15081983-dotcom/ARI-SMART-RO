from django.db import models
from django.utils import timezone

from customers.models import Customer
from employees.models import EmployeeProfile
from service.models import Service


class Complaint(models.Model):

    # ============================================================
    # PRIORITY
    # ============================================================

    PRIORITY_CHOICES = [
        ("NORMAL", "Normal"),
        ("URGENT", "Urgent"),
        ("EMERGENCY", "Emergency"),
    ]

    # ============================================================
    # STATUS
    # ============================================================

    STATUS_CHOICES = [
        ("NEW", "New"),
        ("ASSIGNED", "Assigned"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
        ("CANCELLED", "Cancelled"),
    ]

    # ============================================================
    # COMPLAINT TYPE
    # ============================================================

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

    # ============================================================
    # COMPLAINT ID
    # ============================================================

    complaint_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    # ============================================================
    # CUSTOMER
    # ============================================================

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="complaints",
    )

    # ============================================================
    # ENGINEER
    # ============================================================

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="complaints",
        null=True,
        blank=True,
    )

    # ============================================================
    # COMPLAINT DETAILS
    # ============================================================

    complaint_type = models.CharField(
        max_length=30,
        choices=COMPLAINT_TYPE_CHOICES,
        default="OTHER",
    )

    description = models.TextField(
        blank=True,
    )

    # ============================================================
    # PRIORITY
    # ============================================================

    priority = models.CharField(
        max_length=15,
        choices=PRIORITY_CHOICES,
        default="NORMAL",
    )

    # ============================================================
    # STATUS
    # ============================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="NEW",
    )

    # ============================================================
    # DATES
    # ============================================================

    complaint_date = models.DateTimeField(
        default=timezone.now,
    )

    scheduled_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ============================================================
    # ENGINEER WORK
    # ============================================================

    engineer_remarks = models.TextField(
        blank=True,
    )

    resolution = models.TextField(
        blank=True,
    )

    # ============================================================
    # LOCATION
    # ============================================================

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

    # ============================================================
    # LINKED SERVICE
    # ============================================================

    linked_service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="complaints",
        null=True,
        blank=True,
    )

    # ============================================================
    # SYSTEM DATES
    # ============================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ============================================================
    # AUTO COMPLAINT ID
    # ============================================================

    def save(self, *args, **kwargs):

        if not self.complaint_id:

            year = timezone.now().year

            last = (
                Complaint.objects
                .filter(
                    complaint_id__startswith=
                    f"CMP-{year}"
                )
                .order_by("id")
                .last()
            )

            if last:
                try:
                    number = (
                        int(
                            last.complaint_id
                            .split("-")[-1]
                        )
                        + 1
                    )
                except (
                    ValueError,
                    IndexError,
                ):
                    number = 1
            else:
                number = 1

            self.complaint_id = (
                f"CMP-{year}-{number:06d}"
            )

        # ========================================================
        # AUTO RESOLVED DATE
        # ========================================================

        if (
            self.status == "RESOLVED"
            and self.resolved_date is None
        ):
            self.resolved_date = timezone.now()

        # ========================================================
        # CLEAR RESOLVED DATE IF REOPENED
        # ========================================================

        if self.status not in [
            "RESOLVED",
            "CLOSED",
        ]:
            self.resolved_date = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.complaint_id