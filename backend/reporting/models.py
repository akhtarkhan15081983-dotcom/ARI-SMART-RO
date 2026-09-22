from django.conf import settings
from django.db import models


class ClientErrorEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_error_events",
    )
    company_id = models.PositiveBigIntegerField(null=True, blank=True)
    company_name = models.CharField(max_length=180, blank=True, default="")
    device_id = models.CharField(max_length=128, blank=True, default="")
    platform = models.CharField(max_length=24, blank=True, default="")
    app_version = models.CharField(max_length=32, blank=True, default="")
    app_build = models.CharField(max_length=24, blank=True, default="")
    error_type = models.CharField(max_length=120, blank=True, default="")
    message = models.CharField(max_length=1000)
    stack = models.TextField(blank=True, default="")
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company_id", "created_at"], name="clienterr_company_time_idx"),
            models.Index(fields=["error_type", "created_at"], name="clienterr_type_time_idx"),
        ]

    def __str__(self):
        return f"{self.error_type}: {self.message[:80]}"
