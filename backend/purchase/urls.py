from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SupplierViewSet,
    PurchaseViewSet,
    PurchaseItemViewSet,
)

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
    path("", include(router.urls)),
]