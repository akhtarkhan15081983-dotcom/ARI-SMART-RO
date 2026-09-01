from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SupplierViewSet,
    PurchaseViewSet,
    PurchaseItemViewSet,
)
from .invoice_scan import InvoiceAnalyzeAPIView, InvoiceConfirmAPIView

router = DefaultRouter()

router.register(
    "suppliers",
    SupplierViewSet,
    basename="supplier"
)

router.register(
    "purchases",
    PurchaseViewSet,
    basename="purchase"
)

router.register(
    "purchase-items",
    PurchaseItemViewSet,
    basename="purchase-item"
)

urlpatterns = [
    path("purchases/invoice-scan/analyze/", InvoiceAnalyzeAPIView.as_view(), name="invoice-scan-analyze"),
    path("purchases/invoice-scan/confirm/", InvoiceConfirmAPIView.as_view(), name="invoice-scan-confirm"),
    path("", include(router.urls)),
]
