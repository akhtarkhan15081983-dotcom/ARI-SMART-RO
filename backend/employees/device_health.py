from django.db import models
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from .models import EmployeeProfile
from .views import _request_company


class EmployeeDeviceHealth(models.Model):
    """Latest device/app health snapshot for an employee."""

    employee = models.OneToOneField(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="device_health",
    )
    device_id = models.CharField(max_length=64, blank=True, default="")
    platform = models.CharField(max_length=20, default="ANDROID")
    app_version = models.CharField(max_length=32, blank=True, default="")
    app_build = models.CharField(max_length=24, blank=True, default="")
    os_version = models.CharField(max_length=80, blank=True, default="")
    android_sdk = models.PositiveSmallIntegerField(null=True, blank=True)
    manufacturer = models.CharField(max_length=80, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    low_memory_device = models.BooleanField(default=False)
    memory_class_mb = models.PositiveIntegerField(null=True, blank=True)
    total_memory_mb = models.PositiveIntegerField(null=True, blank=True)
    location_service_enabled = models.BooleanField(default=False)
    location_permission = models.CharField(max_length=24, blank=True, default="")
    background_location_granted = models.BooleanField(default=False)
    notification_permission_granted = models.BooleanField(default=False)
    battery_optimization_ignored = models.BooleanField(default=False)
    live_location_tracking = models.BooleanField(default=False)
    pending_job_actions = models.PositiveIntegerField(default=0)
    pending_location_points = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True, default="")
    reported_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reported_at"]
        indexes = [models.Index(fields=["reported_at"], name="emp_devhealth_seen_idx")]


class EmployeeDeviceHealthAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            employee = request.user.employee_profile
        except Exception:
            return Response({"detail": "Employee profile not found."}, status=404)

        if not employee.is_active or not request.user.is_active:
            return Response({"detail": "Inactive employee cannot report device health."}, status=403)

        payload = request.data if isinstance(request.data, dict) else {}
        row, _ = EmployeeDeviceHealth.objects.get_or_create(employee=employee)
        row.device_id = str(request.headers.get("X-ARI-Device-ID", "") or "")[:64]
        row.platform = str(payload.get("platform") or "ANDROID")[:20]
        row.app_version = str(payload.get("app_version") or "")[:32]
        row.app_build = str(payload.get("app_build") or "")[:24]
        row.os_version = str(payload.get("os_version") or "")[:80]
        row.manufacturer = str(payload.get("manufacturer") or "")[:80]
        row.model = str(payload.get("model") or "")[:120]
        row.location_permission = str(payload.get("location_permission") or "")[:24]
        row.last_error = str(payload.get("last_error") or "")[:500]

        for field in (
            "low_memory_device",
            "location_service_enabled",
            "background_location_granted",
            "notification_permission_granted",
            "battery_optimization_ignored",
            "live_location_tracking",
        ):
            setattr(row, field, bool(payload.get(field, False)))

        for field in (
            "android_sdk",
            "memory_class_mb",
            "total_memory_mb",
            "pending_job_actions",
            "pending_location_points",
        ):
            value = payload.get(field)
            try:
                parsed = None if value in (None, "") else max(0, int(value))
                setattr(row, field, parsed)
            except (TypeError, ValueError):
                if field in {"pending_job_actions", "pending_location_points"}:
                    setattr(row, field, 0)

        row.save()
        return Response({"success": True, "reported_at": row.reported_at})


class AdminDeviceHealthAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        company = _request_company(request)
        if company is None:
            return Response({"detail": "Active company workspace not found."}, status=403)

        now = timezone.now()
        employees = EmployeeProfile.objects.filter(
            company=company,
            is_active=True,
            user__is_active=True,
        ).select_related("user", "device_health").order_by(
            "designation", "user__first_name", "employee_id"
        )

        rows = []
        for employee in employees.iterator(chunk_size=50):
            health = getattr(employee, "device_health", None)
            if health is None:
                status_value = "NEVER_REPORTED"
                age_seconds = None
            else:
                age_seconds = max(0, int((now - health.reported_at).total_seconds()))
                status_value = "HEALTHY" if age_seconds <= 180 else "STALE"

            rows.append({
                "employee_id": employee.id,
                "employee_code": employee.employee_id,
                "name": employee.user.get_full_name() or employee.user.phone,
                "phone": employee.user.phone,
                "designation": employee.designation,
                "attendance_device_bound": bool(employee.attendance_device_id),
                "location_status": (
                    "MISSING"
                    if employee.last_location_updated is None
                    else "LIVE"
                    if now - employee.last_location_updated <= timezone.timedelta(seconds=90)
                    else "STALE"
                ),
                "last_location_updated": employee.last_location_updated,
                "status": status_value,
                "age_seconds": age_seconds,
                "health": None if health is None else {
                    "platform": health.platform,
                    "app_version": health.app_version,
                    "app_build": health.app_build,
                    "os_version": health.os_version,
                    "android_sdk": health.android_sdk,
                    "manufacturer": health.manufacturer,
                    "model": health.model,
                    "low_memory_device": health.low_memory_device,
                    "memory_class_mb": health.memory_class_mb,
                    "total_memory_mb": health.total_memory_mb,
                    "location_service_enabled": health.location_service_enabled,
                    "location_permission": health.location_permission,
                    "background_location_granted": health.background_location_granted,
                    "notification_permission_granted": health.notification_permission_granted,
                    "battery_optimization_ignored": health.battery_optimization_ignored,
                    "live_location_tracking": health.live_location_tracking,
                    "pending_job_actions": health.pending_job_actions,
                    "pending_location_points": health.pending_location_points,
                    "last_error": health.last_error,
                    "reported_at": health.reported_at,
                },
            })
        return Response(rows)
