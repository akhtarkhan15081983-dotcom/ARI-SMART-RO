from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import (
    Supplier,
    Purchase,
    PurchaseItem,
)
from inventory.models import InventoryItem
from .serializers import (
    SupplierSerializer,
    PurchaseSerializer,
    PurchaseItemSerializer,
)

class SupplierViewSet(viewsets.ModelViewSet):

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


class PurchaseViewSet(viewsets.ModelViewSet):

    queryset = Purchase.objects.select_related(
        "supplier"
    ).prefetch_related(
        "items"
    )

    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]


class PurchaseItemViewSet(viewsets.ModelViewSet):

    queryset = PurchaseItem.objects.select_related(
        "purchase",
        "part"
    )

    serializer_class = PurchaseItemSerializer
    permission_classes = [IsAuthenticated]