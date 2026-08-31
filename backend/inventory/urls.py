from django.urls import path

from .views import (
    EngineerBagIssueAPIView,
    OCRVerifyAPIView,
    MyBagAPIView,
    PartCatalogAPIView,
    MyPartRequestsAPIView,
    AdminEngineerBagAPIView,
)

urlpatterns = [
    path("inventory/issue/", EngineerBagIssueAPIView.as_view(), name="inventory-issue"),
    path("inventory/verify/", OCRVerifyAPIView.as_view(), name="inventory-verify"),
    path("inventory/my-bag/", MyBagAPIView.as_view(), name="my-bag"),
    path("inventory/admin/engineer-bags/", AdminEngineerBagAPIView.as_view(), name="admin-engineer-bags"),
    path("inventory/parts/", PartCatalogAPIView.as_view(), name="part-catalog"),
    path("inventory/part-requests/", MyPartRequestsAPIView.as_view(), name="my-part-requests"),
]
