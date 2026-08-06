from django.urls import path
from .views import (
    InstallationCreateAPIView,
    InstallationPartCreateAPIView,
    CompleteInstallationAPIView,
)

urlpatterns = [
    path(
        "",
        InstallationCreateAPIView.as_view(),
        name="installation-create",
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
]