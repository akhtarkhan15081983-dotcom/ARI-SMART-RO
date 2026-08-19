from django.urls import path

from .views import (
    ServiceListAPIView,
    ServiceCreateAPIView,
    ServiceDetailAPIView,
    ServiceUpdateAPIView,
    CompleteServiceAPIView,
    ServiceSearchAPIView,
    ServiceExportAPIView,
)

urlpatterns = [

    path(
        "",
        ServiceListAPIView.as_view(),
        name="service-list",
    ),

    path(
        "create/",
        ServiceCreateAPIView.as_view(),
        name="service-create",
    ),

    path(
        "<int:pk>/",
        ServiceDetailAPIView.as_view(),
        name="service-detail",
    ),

    path(
        "<int:pk>/update/",
        ServiceUpdateAPIView.as_view(),
        name="service-update",
    ),

    path(
        "<int:pk>/complete/",
        CompleteServiceAPIView.as_view(),
        name="service-complete",
    ),

    path(
        "search/",
        ServiceSearchAPIView.as_view(),
        name="service-search",
    ),
    path(
        "export/",
        ServiceExportAPIView.as_view(),
        name="service-export",
    ),
]