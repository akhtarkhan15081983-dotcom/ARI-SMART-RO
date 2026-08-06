from rest_framework import serializers

from .models import (
    Supplier,
    Purchase,
    PurchaseItem,
)
from inventory.models import InventoryItem


class SupplierSerializer(serializers.ModelSerializer):

    class Meta:
        model = Supplier
        fields = "__all__"


class PurchaseItemSerializer(serializers.ModelSerializer):

    part_name = serializers.CharField(
        source="part.name",
        read_only=True
    )

    class Meta:
        model = PurchaseItem
        fields = "__all__"
        extra_kwargs = {
            "purchase": {
                "read_only": True
            }
        }

class PurchaseSerializer(serializers.ModelSerializer):

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
    )

    items = PurchaseItemSerializer(
        many=True
    )

    def create(self, validated_data):
        items_data = validated_data.pop("items")

        purchase = Purchase.objects.create(**validated_data)

        for item in items_data:
            purchase_item = PurchaseItem.objects.create(
                purchase=purchase,
                **item
            )

            part = purchase_item.part

            if part.is_serialized:
                for i in range(purchase_item.quantity):
                    InventoryItem.objects.create(
                        purchase_item=purchase_item,
                        part=part,
                        serial_number=None
                    )
            else:
                for i in range(purchase_item.quantity):
                    InventoryItem.objects.create(
                        purchase_item=purchase_item,
                        part=part,
                        serial_number=None
                    )
        return purchase

    class Meta:
        model = Purchase
        fields = "__all__"