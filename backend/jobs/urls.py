from django.urls import include, path
from rest_framework.routers import DefaultRouter


from .views import (
    JobViewSet,
    MyJobsAPIView,
    JobDetailAPIView,
    JobAcceptAPIView,
    JobChangeStatusAPIView,
    JobMediaUploadAPIView,
    JobGPSUploadAPIView,
    JobPartUsedAPIView,
    JobSignatureUploadAPIView,
)
router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="jobs")

urlpatterns = [
    path("jobs/my-jobs/", MyJobsAPIView.as_view(), name="my-jobs"),

    path(
        "jobs/<int:pk>/accept/",
        JobAcceptAPIView.as_view(),
        name="job-accept",
    ),

    path(
        "jobs/<int:pk>/change-status/",
        JobChangeStatusAPIView.as_view(),
        name="job-change-status",
    ),

    path(
        "jobs/<int:pk>/media/",
        JobMediaUploadAPIView.as_view(),
        name="job-media-upload",
    ),

    path(
        "jobs/<int:pk>/gps/",
        JobGPSUploadAPIView.as_view(),
        name="job-gps-upload",
    ),

    path(
        "jobs/<int:pk>/parts/",
        JobPartUsedAPIView.as_view(),
        name="job-parts-used",
    ),

    path(
        "jobs/<int:pk>/signature/",
        JobSignatureUploadAPIView.as_view(),
        name="job-signature-upload",
    ),
    
    path("", include(router.urls)),

    path(
        "jobs/<int:pk>/",
        JobDetailAPIView.as_view(),
        name="job-detail",
    ),
]