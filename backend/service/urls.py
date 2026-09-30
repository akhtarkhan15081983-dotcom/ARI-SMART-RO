from django.urls import path

from .views import (
    CompleteServiceAPIView,
    ROHealthAPIView,
    ServiceDetailAPIView,
    ServiceExportAPIView,
    ServiceIntervalPolicyAPIView,
    ServiceListAPIView,
    ServiceSearchAPIView,
)
from .security_views import SecureServiceCreateAPIView, SecureServiceUpdateAPIView

urlpatterns = [
    path("", ServiceListAPIView.as_view(), name="service-list"),
    path("create/", SecureServiceCreateAPIView.as_view(), name="service-create"),
    path("ro-health/<str:asset_id>/", ROHealthAPIView.as_view(), name="ro-health"),
    path("interval-policies/", ServiceIntervalPolicyAPIView.as_view(), name="service-interval-policies"),
    path("<int:pk>/", ServiceDetailAPIView.as_view(), name="service-detail"),
    path("<int:pk>/update/", SecureServiceUpdateAPIView.as_view(), name="service-update"),
    path("<int:pk>/complete/", CompleteServiceAPIView.as_view(), name="service-complete"),
    path("search/", ServiceSearchAPIView.as_view(), name="service-search"),
    path("export/", ServiceExportAPIView.as_view(), name="service-export"),
]
