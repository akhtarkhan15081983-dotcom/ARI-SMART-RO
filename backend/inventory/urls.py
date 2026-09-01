from django.urls import path

from .views import (
    EngineerBagIssueAPIView,
    OCRVerifyAPIView,
    MyBagAPIView,
    PartCatalogAPIView,
    MyPartRequestsAPIView,
    AdminEngineerBagAPIView,
    PartRequestApprovalInboxAPIView, PartRequestReviewAPIView,
    InventoryReceivingQueueAPIView, InventoryReceiveAPIView, PartRequestFulfilAPIView,
)
from .reports import (
    InventoryCodeGenerationAPIView, InventoryQrLabelsPdfAPIView,
    InventorySummaryAPIView, InventoryExcelReportAPIView,
)

urlpatterns = [
    path("inventory/issue/", EngineerBagIssueAPIView.as_view(), name="inventory-issue"),
    path("inventory/verify/", OCRVerifyAPIView.as_view(), name="inventory-verify"),
    path("inventory/my-bag/", MyBagAPIView.as_view(), name="my-bag"),
    path("inventory/admin/engineer-bags/", AdminEngineerBagAPIView.as_view(), name="admin-engineer-bags"),
    path("inventory/parts/", PartCatalogAPIView.as_view(), name="part-catalog"),
    path("inventory/part-requests/", MyPartRequestsAPIView.as_view(), name="my-part-requests"),
    path("inventory/workflow/requests/", PartRequestApprovalInboxAPIView.as_view(), name="part-request-approval-inbox"),
    path("inventory/workflow/requests/<int:request_id>/review/", PartRequestReviewAPIView.as_view(), name="part-request-review"),
    path("inventory/workflow/requests/<int:request_id>/fulfil/", PartRequestFulfilAPIView.as_view(), name="part-request-fulfil"),
    path("inventory/workflow/receiving/", InventoryReceivingQueueAPIView.as_view(), name="inventory-receiving-queue"),
    path("inventory/workflow/receive/", InventoryReceiveAPIView.as_view(), name="inventory-receive"),
    path("inventory/workflow/generate-codes/", InventoryCodeGenerationAPIView.as_view(), name="inventory-generate-codes"),
    path("inventory/workflow/qr-labels.pdf", InventoryQrLabelsPdfAPIView.as_view(), name="inventory-qr-labels"),
    path("inventory/workflow/summary/", InventorySummaryAPIView.as_view(), name="inventory-summary"),
    path("inventory/workflow/reports/inventory.xlsx", InventoryExcelReportAPIView.as_view(), name="inventory-excel-report"),
]
