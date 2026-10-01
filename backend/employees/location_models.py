from django.db import models

from .models import EmployeeProfile


class EmployeeLocationPoint(models.Model):
    """One GPS point captured while an employee is actively sharing a work shift."""

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="location_points",
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    captured_at = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "employees"
        ordering = ["captured_at", "id"]
        indexes = [
            models.Index(
                fields=["employee", "captured_at"],
                name="emp_loc_employee_time_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "captured_at", "latitude", "longitude"],
                name="unique_employee_location_point",
            ),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} @ {self.captured_at}"
