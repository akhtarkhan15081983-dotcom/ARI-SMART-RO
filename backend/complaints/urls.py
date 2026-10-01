from django.urls import path

from .assistant_views import ComplaintAssistantAPIView
from .diagnosis_views import ComplaintDiagnosisAssistAPIView
from .views import (
    ComplaintStartAPIView,
    ComplaintResolveAPIView,
    ComplaintCloseAPIView,
)
from .customer_scope import (
    SecureComplaintListAPIView,
    SecureComplaintCreateAPIView,
    SecureComplaintDetailAPIView,
    SecureComplaintSearchAPIView,
)
from .security_views import (
    SecureComplaintUpdateAPIView,
    TenantScopedComplaintAssignEngineerAPIView,
)


urlpatterns = [
    path("", SecureComplaintListAPIView.as_view(), name="complaint-list"),
    path("assistant/", ComplaintAssistantAPIView.as_view(), name="complaint-assistant"),
    path("create/", SecureComplaintCreateAPIView.as_view(), name="complaint-create"),
    path("<int:pk>/diagnosis-assist/", ComplaintDiagnosisAssistAPIView.as_view(), name="complaint-diagnosis-assist"),
    path("<int:pk>/", SecureComplaintDetailAPIView.as_view(), name="complaint-detail"),
    path("<int:pk>/update/", SecureComplaintUpdateAPIView.as_view(), name="complaint-update"),
    path(
        "<int:pk>/assign/",
        TenantScopedComplaintAssignEngineerAPIView.as_view(),
        name="complaint-assign-engineer",
    ),
    path("<int:pk>/start/", ComplaintStartAPIView.as_view(), name="complaint-start"),
    path("<int:pk>/resolve/", ComplaintResolveAPIView.as_view(), name="complaint-resolve"),
    path("<int:pk>/close/", ComplaintCloseAPIView.as_view(), name="complaint-close"),
    path("search/", SecureComplaintSearchAPIView.as_view(), name="complaint-search"),
]
