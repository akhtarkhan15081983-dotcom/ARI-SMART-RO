from django.urls import path

from .views import (
    ComplaintListAPIView,
    ComplaintCreateAPIView,
    ComplaintDetailAPIView,
    ComplaintUpdateAPIView,
    ComplaintAssignEngineerAPIView,
    ComplaintStartAPIView,
    ComplaintResolveAPIView,
    ComplaintCloseAPIView,
    ComplaintSearchAPIView,

)


urlpatterns = [

    path(
        "",
        ComplaintListAPIView.as_view(),
        name="complaint-list",
    ),

    path(
        "create/",
        ComplaintCreateAPIView.as_view(),
        name="complaint-create",
    ),

    path(
        "<int:pk>/",
        ComplaintDetailAPIView.as_view(),
        name="complaint-detail",
    ),

    path(
        "<int:pk>/update/",
        ComplaintUpdateAPIView.as_view(),
        name="complaint-update",
    ),

    path(
        "<int:pk>/assign/",
        ComplaintAssignEngineerAPIView.as_view(),
        name="complaint-assign-engineer",
    ),

    path(
        "<int:pk>/start/",
        ComplaintStartAPIView.as_view(),
        name="complaint-start",
    ),

    path(
        "<int:pk>/resolve/",
        ComplaintResolveAPIView.as_view(),
        name="complaint-resolve",
    ),

    path(
        "<int:pk>/close/",
        ComplaintCloseAPIView.as_view(),
        name="complaint-close",
    ),

    path(
        "search/",
        ComplaintSearchAPIView.as_view(),
        name="complaint-search",
    ),
]