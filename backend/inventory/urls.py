from django.urls import path

from .views import (
    OCRVerifyAPIView,
    MyBagAPIView,
    PartCatalogAPIView,
)
from .security_views import (
    TenantScopedEngineerBagIssueAPIView,
    TenantScopedAdminEngineerBagAPIView,
    TenantScopedMyPartRequestsAPIView,
    TenantScopedPartRequestApprovalInboxAPIView,
    TenantScopedPartRequestReviewAPIView,
    TenantScopedPartRequestFulfilAPIView,
)
from .warehouse_security_views import (
    TenantScopedInventoryReceivingQueueAPIView,
    TenantScopedInventoryReceiveAPIView,
    TenantScopedInventoryPhotoReceiveAPIView,
    TenantScopedInventoryCodeGenerationAPIView,
    TenantScopedInventoryQrLabelsPdfAPIView,
    TenantScopedInventorySummaryAPIView,
    TenantScopedInventoryExcelReportAPIView,
)

urlpatterns = [
    path("inventory/issue/", TenantScopedEngineerBagIssueAPIView.as_view(), name="inventory-issue"),
    path("inventory/verify/", OCRVerifyAPIView.as_view(), name="inventory-verify"),
    path("inventory/my-bag/", MyBagAPIView.as_view(), name="my-bag"),
    path("inventory/admin/engineer-bags/", TenantScopedAdminEngineerBagAPIView.as_view(), name="admin-engineer-bags"),
    path("inventory/parts/", PartCatalogAPIView.as_view(), name="part-catalog"),
    path("inventory/part-requests/", TenantScopedMyPartRequestsAPIView.as_view(), name="my-part-requests"),
    path("inventory/workflow/requests/", TenantScopedPartRequestApprovalInboxAPIView.as_view(), name="part-request-approval-inbox"),
    path("inventory/workflow/requests/<int:request_id>/review/", TenantScopedPartRequestReviewAPIView.as_view(), name="part-request-review"),
    path("inventory/workflow/requests/<int:request_id>/fulfil/", TenantScopedPartRequestFulfilAPIView.as_view(), name="part-request-fulfil"),
    path("inventory/workflow/receiving/", TenantScopedInventoryReceivingQueueAPIView.as_view(), name="inventory-receiving-queue"),
    path("inventory/workflow/receive/", TenantScopedInventoryReceiveAPIView.as_view(), name="inventory-receive"),
    path("inventory/workflow/receive-photo/", TenantScopedInventoryPhotoReceiveAPIView.as_view(), name="inventory-photo-receive"),
    path("inventory/workflow/generate-codes/", TenantScopedInventoryCodeGenerationAPIView.as_view(), name="inventory-generate-codes"),
    path("inventory/workflow/qr-labels.pdf", TenantScopedInventoryQrLabelsPdfAPIView.as_view(), name="inventory-qr-labels"),
    path("inventory/workflow/summary/", TenantScopedInventorySummaryAPIView.as_view(), name="inventory-summary"),
    path("inventory/workflow/reports/inventory.xlsx", TenantScopedInventoryExcelReportAPIView.as_view(), name="inventory-excel-report"),
]
