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

    regular_shift_end_at = models.DateTimeField(null=True, blank=True)
    regular_working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    overtime_working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    auto_checked_out = models.BooleanField(default=False)
    checkout_reason = models.CharField(
        max_length=24,
        choices=[
            ("", "Not checked out"),
            ("MANUAL", "Manual checkout"),
            ("AUTO_8_HOURS", "Automatic regular shift checkout"),
        ],
        blank=True,
        default="",
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


class OvertimeRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending admin approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    END_REASON_CHOICES = [
        ("", "Not ended"),
        ("MANUAL", "Employee ended overtime"),
        ("AUTO_APPROVED_LIMIT", "Approved overtime limit reached"),
    ]

    attendance = models.OneToOneField(
        Attendance,
        on_delete=models.CASCADE,
        related_name="overtime_request",
    )
    requested_hours = models.DecimalField(max_digits=4, decimal_places=2, default=1)
    approved_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_overtime_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    planned_end_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(
        max_length=24,
        choices=END_REASON_CHOICES,
        blank=True,
        default="",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return (
            f"{self.attendance.employee.employee_id} - "
            f"{self.attendance.date} - {self.status}"
        )


class AttendanceDeviceOverride(models.Model):
    """Admin-approved emergency use of a non-enrolled phone for one date."""

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="attendance_device_overrides",
    )
    date = models.DateField()
    is_active = models.BooleanField(default=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_attendance_device_overrides",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "employee__employee_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "date"],
                name="unique_employee_attendance_device_override_date",
            )
        ]

    def __str__(self):
        state = "active" if self.is_active else "revoked"
        return f"{self.employee.employee_id} - {self.date} - {state}"
