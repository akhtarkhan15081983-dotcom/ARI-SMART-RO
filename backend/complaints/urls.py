from django.urls import path

from .customer_scope import (
    SecureComplaintListAPIView,
    SecureComplaintCreateAPIView,
    SecureComplaintDetailAPIView,
    SecureComplaintSearchAPIView,
)
from .security_views import (
    SecureComplaintUpdateAPIView,
    TenantScopedComplaintAssignEngineerAPIView,
    TenantScopedComplaintCloseAPIView,
    TenantScopedComplaintResolveAPIView,
    TenantScopedComplaintStartAPIView,
)


urlpatterns = [
    path("", SecureComplaintListAPIView.as_view(), name="complaint-list"),
    path("create/", SecureComplaintCreateAPIView.as_view(), name="complaint-create"),
    path("<int:pk>/", SecureComplaintDetailAPIView.as_view(), name="complaint-detail"),
    path("<int:pk>/update/", SecureComplaintUpdateAPIView.as_view(), name="complaint-update"),
    path(
        "<int:pk>/assign/",
        TenantScopedComplaintAssignEngineerAPIView.as_view(),
        name="complaint-assign-engineer",
    ),
    path("<int:pk>/start/", TenantScopedComplaintStartAPIView.as_view(), name="complaint-start"),
    path("<int:pk>/resolve/", TenantScopedComplaintResolveAPIView.as_view(), name="complaint-resolve"),
    path("<int:pk>/close/", TenantScopedComplaintCloseAPIView.as_view(), name="complaint-close"),
    path("search/", SecureComplaintSearchAPIView.as_view(), name="complaint-search"),
]
