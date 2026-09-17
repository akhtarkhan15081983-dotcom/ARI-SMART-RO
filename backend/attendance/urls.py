from django.urls import path

from .views import (
    CheckInAPIView,
    CheckOutAPIView,
    TodayAttendanceAPIView,
    AttendanceHistoryAPIView,
    AdminAttendanceReviewListAPIView,
    AdminAttendanceReviewActionAPIView,
    AdminAttendanceDeviceOverrideAPIView,
)

urlpatterns = [
    path("check-in/", CheckInAPIView.as_view(), name="attendance-check-in"),
    path("check-out/", CheckOutAPIView.as_view(), name="attendance-check-out"),
    path("today/", TodayAttendanceAPIView.as_view(), name="attendance-today"),
    path("history/", AttendanceHistoryAPIView.as_view(), name="attendance-history"),
    path(
        "admin/device-overrides/",
        AdminAttendanceDeviceOverrideAPIView.as_view(),
        name="admin-attendance-device-overrides",
    ),
    path(
        "admin/device-overrides/<int:employee_id>/",
        AdminAttendanceDeviceOverrideAPIView.as_view(),
        name="admin-attendance-device-override-action",
    ),
    path("admin/reviews/", AdminAttendanceReviewListAPIView.as_view(), name="admin-attendance-reviews"),
    path("admin/reviews/<int:attendance_id>/", AdminAttendanceReviewActionAPIView.as_view(), name="admin-attendance-review-action"),
]
