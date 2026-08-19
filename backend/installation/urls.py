from django.urls import path
from .views import (
    InstallationListAPIView,
    InstallationCreateAPIView,
    InstallationDetailAPIView,
    InstallationUpdateAPIView,
    InstallationPartCreateAPIView,
    CompleteInstallationAPIView,
    InstallationSearchAPIView,
    InstallationDashboardAPIView,
)


urlpatterns = [
    path(
        "dashboard/",
        InstallationDashboardAPIView.as_view(),
        name="installation-dashboard",
    ),
    path(
        "",
        InstallationListAPIView.as_view(),
        name="installation-list",
    ),

    

    path(
        "create/",
        InstallationCreateAPIView.as_view(),
        name="installation-create",
    ),

    path(
        "<int:pk>/",
        InstallationDetailAPIView.as_view(),
        name="installation-detail",
    ),

    path(
        "<int:pk>/update/",
        InstallationUpdateAPIView.as_view(),
        name="installation-update",
    ),

    path(
        "parts/",
        InstallationPartCreateAPIView.as_view(),
        name="installation-part-create",
    ),

    path(
        "complete/",
        CompleteInstallationAPIView.as_view(),
        name="installation-complete",
    ),

    path(
        "search/",
        InstallationSearchAPIView.as_view(),
        name="installation-search",
    ),

]