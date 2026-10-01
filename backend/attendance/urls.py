from django.urls import path

from .offline_hardened import OfflineAttendanceSyncAPIView
from .security_views import SecureCheckInAPIView
from .tenant_security import (
    TenantScopedAttendanceDeviceOverrideAPIView,
    TenantScopedAttendanceReviewListAPIView,
    TenantScopedAttendanceReviewActionAPIView,
)
from .views import (
    CheckOutAPIView,
    TodayAttendanceAPIView,
    AttendanceHistoryAPIView,
    OvertimeRequestAPIView,
    OvertimeStartAPIView,
    OvertimeStopAPIView,
    AdminOvertimeAPIView,
)

urlpatterns = [
    path("check-in/", SecureCheckInAPIView.as_view(), name="attendance-check-in"),
    path("check-out/", CheckOutAPIView.as_view(), name="attendance-check-out"),
    path("offline-sync/", OfflineAttendanceSyncAPIView.as_view(), name="attendance-offline-sync"),
    path("today/", TodayAttendanceAPIView.as_view(), name="attendance-today"),
    path("history/", AttendanceHistoryAPIView.as_view(), name="attendance-history"),
    path("overtime/", OvertimeRequestAPIView.as_view(), name="attendance-overtime-request"),
    path("overtime/start/", OvertimeStartAPIView.as_view(), name="attendance-overtime-start"),
    path("overtime/stop/", OvertimeStopAPIView.as_view(), name="attendance-overtime-stop"),
    path("admin/overtime/", AdminOvertimeAPIView.as_view(), name="admin-attendance-overtime"),
    path("admin/overtime/<int:request_id>/", AdminOvertimeAPIView.as_view(), name="admin-attendance-overtime-action"),
    path(
        "admin/device-overrides/",
        TenantScopedAttendanceDeviceOverrideAPIView.as_view(),
        name="admin-attendance-device-overrides",
    ),
    path(
        "admin/device-overrides/<int:employee_id>/",
        TenantScopedAttendanceDeviceOverrideAPIView.as_view(),
        name="admin-attendance-device-override-action",
    ),
    path(
        "admin/reviews/",
        TenantScopedAttendanceReviewListAPIView.as_view(),
        name="admin-attendance-reviews",
    ),
    path(
        "admin/reviews/<int:attendance_id>/",
        TenantScopedAttendanceReviewActionAPIView.as_view(),
        name="admin-attendance-review-action",
    ),
]
