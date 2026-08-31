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
    JobSearchAPIView,
    GenerateOTPAPIView,
    VerifyOTPAPIView,
)
from .work_planner import WorkCalendarAPIView, WorkRescheduleAPIView, WorkRouteAPIView
router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="jobs")

urlpatterns = [
    path("work-planner/calendar/", WorkCalendarAPIView.as_view(), name="work-calendar"),
    path("work-planner/reschedule/", WorkRescheduleAPIView.as_view(), name="work-reschedule"),
    path("work-planner/route/", WorkRouteAPIView.as_view(), name="work-route"),
    path("jobs/my-jobs/", MyJobsAPIView.as_view(), name="my-jobs"),
    path(
        "jobs/search/",
        JobSearchAPIView.as_view(),
        name="job-search",
    ),

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

    path(
        "jobs/<int:pk>/generate-otp/",
        GenerateOTPAPIView.as_view(),
    ),

    path(
        "jobs/<int:pk>/verify-otp/",
        VerifyOTPAPIView.as_view(),
    ),
]
