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

    # V5 telemetry is intentionally nullable/additive so legacy mobile clients
    # and existing route rows remain valid during a staged rollout.
    accuracy_m = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=32, blank=True, default="")
    speed_mps = models.FloatField(null=True, blank=True)
    heading_degrees = models.FloatField(null=True, blank=True)
    motion_state = models.CharField(max_length=16, blank=True, default="")
    quality_label = models.CharField(max_length=16, blank=True, default="")
    client_point_id = models.CharField(max_length=96, null=True, blank=True)
    client_sequence = models.BigIntegerField(null=True, blank=True)
    altitude_m = models.FloatField(null=True, blank=True)
    client_platform = models.CharField(max_length=16, blank=True, default="")

    class Meta:
        app_label = "employees"
        ordering = ["captured_at", "id"]
        indexes = [
            models.Index(
                fields=["employee", "captured_at"],
                name="emp_loc_employee_time_idx",
            ),
            models.Index(
                fields=["employee", "client_sequence"],
                name="emp_loc_employee_seq_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "captured_at", "latitude", "longitude"],
                name="unique_employee_location_point",
            ),
            models.UniqueConstraint(
                fields=["employee", "client_point_id"],
                condition=models.Q(client_point_id__isnull=False),
                name="unique_employee_client_point",
            ),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} @ {self.captured_at}"
