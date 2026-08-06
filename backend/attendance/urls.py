from django.urls import path

from .views import (
    CheckInAPIView,
    CheckOutAPIView,
    TodayAttendanceAPIView,
    AttendanceHistoryAPIView,
)

urlpatterns = [

    path(
        "check-in/",
        CheckInAPIView.as_view(),
        name="attendance-check-in",
    ),

    path(
        "check-out/",
        CheckOutAPIView.as_view(),
        name="attendance-check-out",
    ),

    path(
        "today/",
        TodayAttendanceAPIView.as_view(),
        name="attendance-today",
    ),

    path(
        "history/",
        AttendanceHistoryAPIView.as_view(),
        name="attendance-history",
    ),

]