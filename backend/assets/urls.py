from django.urls import path

from .views import (
    ROAssetAllocateAPIView,
    ROAssetListAPIView,
    ROAssetMovementListAPIView,
    ROAssetReceiveAPIView,
    ROAssetRestockAPIView,
    ROAssetReturnAPIView,
    ROAssetWorkflowSummaryAPIView,
)

urlpatterns = [
    path("", ROAssetListAPIView.as_view(), name="asset-list"),
    path("workflow/summary/", ROAssetWorkflowSummaryAPIView.as_view(), name="asset-workflow-summary"),
    path("workflow/receive/", ROAssetReceiveAPIView.as_view(), name="asset-receive"),
    path("workflow/<int:asset_id>/allocate/", ROAssetAllocateAPIView.as_view(), name="asset-allocate"),
    path("workflow/<int:asset_id>/return/", ROAssetReturnAPIView.as_view(), name="asset-return"),
    path("workflow/<int:asset_id>/restock/", ROAssetRestockAPIView.as_view(), name="asset-restock"),
    path("workflow/movements/", ROAssetMovementListAPIView.as_view(), name="asset-movements"),
]
