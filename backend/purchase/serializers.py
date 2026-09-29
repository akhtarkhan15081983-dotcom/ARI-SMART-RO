from uuid import uuid4

from django.utils import timezone
from rest_framework import serializers

from .models import Supplier, Purchase, PurchaseItem
from inventory.models import InventoryItem


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ("company",)


class PurchaseItemSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = "__all__"
        read_only_fields = ("company", "purchase")


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    invoice_number = serializers.CharField(required=False, allow_blank=True)
    items = PurchaseItemSerializer(many=True)

    def validate_supplier(self, supplier):
        request = self.context.get("request")
        company = getattr(request, "ari_company", None) if request is not None else None
        if company is not None and supplier.company_id != company.id:
            raise serializers.ValidationError("Supplier does not belong to this workspace.")
        if company is None and supplier.company_id is not None:
            raise serializers.ValidationError("Supplier does not belong to the legacy workspace.")
        return supplier

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
                company=purchase.company,
                **item,
            )
            part = purchase_item.part
            for _ in range(purchase_item.quantity):
                if part.is_serialized:
                    while True:
                        code = f"ARI-{part.code}-{uuid4().hex[:10].upper()}"
                        if not InventoryItem.objects.filter(serial_number=code).exists():
                            break
                    InventoryItem.objects.create(
                        company=purchase.company,
                        purchase_item=purchase_item,
                        part=part,
                        serial_number=code,
                        barcode=code,
                    )
                else:
                    InventoryItem.objects.create(
                        company=purchase.company,
                        purchase_item=purchase_item,
                        part=part,
                        serial_number=None,
                    )
        return purchase

    class Meta:
        model = Purchase
        fields = "__all__"
        read_only_fields = (
            "company",
            "entry_source",
            "ocr_text",
            "ocr_confidence",
            "verified_by",
            "verified_at",
        )
