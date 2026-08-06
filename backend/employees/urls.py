from django.urls import path

from .views import (
    UpdateLiveLocationAPIView,
    EngineerLiveMapAPIView,
    EmployeeProfileAPIView,
)

urlpatterns = [

    path(
        "employees/live-location/",
        UpdateLiveLocationAPIView.as_view(),
        name="live-location",
    ),

    path(
        "employees/live-map/",
        EngineerLiveMapAPIView.as_view(),
        name="live-map",
    ),

    path(
        "employees/profile/",
        EmployeeProfileAPIView.as_view(),
        name="employee-profile",
    ),

]