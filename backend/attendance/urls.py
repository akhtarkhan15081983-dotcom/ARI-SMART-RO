from django.urls import path

from .views import (
    CheckInAPIView,
    CheckOutAPIView,
    TodayAttendanceAPIView,
    AttendanceHistoryAPIView,
    AdminAttendanceReviewListAPIView,
    AdminAttendanceReviewActionAPIView,
)

urlpatterns = [
    path("check-in/", CheckInAPIView.as_view(), name="attendance-check-in"),
    path("check-out/", CheckOutAPIView.as_view(), name="attendance-check-out"),
    path("today/", TodayAttendanceAPIView.as_view(), name="attendance-today"),
    path("history/", AttendanceHistoryAPIView.as_view(), name="attendance-history"),
    path("admin/reviews/", AdminAttendanceReviewListAPIView.as_view(), name="admin-attendance-reviews"),
    path("admin/reviews/<int:attendance_id>/", AdminAttendanceReviewActionAPIView.as_view(), name="admin-attendance-review-action"),
]
