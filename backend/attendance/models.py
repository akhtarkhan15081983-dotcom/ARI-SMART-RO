from django.db import models
from django.conf import settings
from employees.models import EmployeeProfile


class Attendance(models.Model):

    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("HALF_DAY", "Half Day"),
        ("LEAVE", "Leave"),
    ]

    IDENTITY_REVIEW_CHOICES = [
        ("PENDING", "Pending human review"),
        ("APPROVED", "Approved by admin"),
        ("REJECTED", "Rejected by admin"),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="attendance",
    )

    date = models.DateField()

    check_in = models.DateTimeField(
        null=True,
        blank=True,
    )

    check_out = models.DateTimeField(
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

    selfie = models.ImageField(
        upload_to="attendance/",
        blank=True,
        null=True,
    )

    identity_review_status = models.CharField(
        max_length=20,
        choices=IDENTITY_REVIEW_CHOICES,
        default="PENDING",
    )
    identity_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_identity_reviews",
    )
    identity_reviewed_at = models.DateTimeField(null=True, blank=True)
    identity_review_note = models.CharField(max_length=255, blank=True, default="")

    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PRESENT",
    )

    remarks = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} - {self.date}"
