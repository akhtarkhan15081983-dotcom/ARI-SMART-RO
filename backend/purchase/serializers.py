from uuid import uuid4

from django.utils import timezone
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
    invoice_number = serializers.CharField(required=False, allow_blank=True)

    items = PurchaseItemSerializer(
        many=True
    )

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        invoice_number = str(validated_data.get("invoice_number") or "").strip()
        if not invoice_number:
            stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
            validated_data["invoice_number"] = f"NO-BILL-{stamp}-{uuid4().hex[:6].upper()}"
        else:
            validated_data["invoice_number"] = invoice_number

        purchase = Purchase.objects.create(**validated_data)

        for item in items_data:
            purchase_item = PurchaseItem.objects.create(
                purchase=purchase,
                **item
            )

            part = purchase_item.part

            for i in range(purchase_item.quantity):
                if part.is_serialized:
                    while True:
                        code = f"ARI-{part.code}-{uuid4().hex[:10].upper()}"
                        if not InventoryItem.objects.filter(serial_number=code).exists():
                            break
                    InventoryItem.objects.create(
                        purchase_item=purchase_item,
                        part=part,
                        serial_number=code,
                        barcode=code,
                    )
                else:
                    InventoryItem.objects.create(
                        purchase_item=purchase_item,
                        part=part,
                        serial_number=None,
                    )
        return purchase

    class Meta:
        model = Purchase
        fields = "__all__"
        read_only_fields = ("entry_source", "ocr_text", "ocr_confidence", "verified_by", "verified_at")
