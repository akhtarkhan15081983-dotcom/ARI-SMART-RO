from django.urls import path

from .views import (
    UpdateLiveLocationAPIView,
    EngineerLiveMapAPIView,
    EmployeeProfileAPIView,
    EngineerListAPIView,
    AssignmentEmployeeListAPIView,
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

    path(
        "employees/engineers/",
        EngineerListAPIView.as_view(),
        name="engineer-list",
    ),

    path(
        "employees/assignment-employees/",
        AssignmentEmployeeListAPIView.as_view(),
        name="assignment-employees",
    ),

]