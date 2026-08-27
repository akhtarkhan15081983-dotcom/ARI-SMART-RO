from rest_framework import viewsets

from accounts.permissions import IsStaffOperator
from .models import Supplier, Purchase, PurchaseItem
from .serializers import SupplierSerializer, PurchaseSerializer, PurchaseItemSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsStaffOperator]


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.select_related("supplier").prefetch_related("items")
    serializer_class = PurchaseSerializer
    permission_classes = [IsStaffOperator]


class PurchaseItemViewSet(viewsets.ModelViewSet):
    queryset = PurchaseItem.objects.select_related("purchase", "part")
    serializer_class = PurchaseItemSerializer
    permission_classes = [IsStaffOperator]
