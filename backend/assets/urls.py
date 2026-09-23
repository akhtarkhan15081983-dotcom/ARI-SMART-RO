from django.urls import path

from .passport_views import ROAssetPassportLookupAPIView
from .views import (
    ROAssetAllocateAPIView,
    ROAssetListAPIView,
    ROAssetMovementListAPIView,
    ROAssetQCAPIView,
    ROAssetReceiveAPIView,
    ROAssetReserveAPIView,
    ROAssetRestockAPIView,
    ROAssetReturnAPIView,
    ROAssetWorkflowSummaryAPIView,
    ROStockAuditAPIView,
    ROStockAuditCompleteAPIView,
    ROStockAuditScanAPIView,
)

urlpatterns = [
    path("", ROAssetListAPIView.as_view(), name="asset-list"),
    path("passport/lookup/", ROAssetPassportLookupAPIView.as_view(), name="asset-passport-lookup"),
    path("workflow/summary/", ROAssetWorkflowSummaryAPIView.as_view(), name="asset-workflow-summary"),
    path("workflow/receive/", ROAssetReceiveAPIView.as_view(), name="asset-receive"),
    path("workflow/<int:asset_id>/qc/", ROAssetQCAPIView.as_view(), name="asset-qc"),
    path("workflow/<int:asset_id>/reserve/", ROAssetReserveAPIView.as_view(), name="asset-reserve"),
    path("workflow/<int:asset_id>/allocate/", ROAssetAllocateAPIView.as_view(), name="asset-allocate"),
    path("workflow/<int:asset_id>/return/", ROAssetReturnAPIView.as_view(), name="asset-return"),
    path("workflow/<int:asset_id>/restock/", ROAssetRestockAPIView.as_view(), name="asset-restock"),
    path("workflow/movements/", ROAssetMovementListAPIView.as_view(), name="asset-movements"),
    path("workflow/audits/", ROStockAuditAPIView.as_view(), name="asset-stock-audits"),
    path("workflow/audits/<int:audit_id>/scan/", ROStockAuditScanAPIView.as_view(), name="asset-stock-audit-scan"),
    path("workflow/audits/<int:audit_id>/complete/", ROStockAuditCompleteAPIView.as_view(), name="asset-stock-audit-complete"),
]
