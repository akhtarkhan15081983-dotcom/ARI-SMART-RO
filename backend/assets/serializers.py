from rest_framework import serializers

from .models import (
    ROAsset,
    ROAssetComponent,
    ROAssetComponentEvent,
    ROAssetMovement,
)


class ROAssetComponentSerializer(serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    part_name = serializers.CharField(source="part.name", read_only=True)
    part_brand = serializers.CharField(source="part.brand", read_only=True)
    part_unit = serializers.CharField(source="part.unit", read_only=True)
    is_serialized = serializers.BooleanField(source="part.is_serialized", read_only=True)
    inventory_serial = serializers.CharField(
        source="inventory_item.serial_number", read_only=True, default=""
    )

    class Meta:
        model = ROAssetComponent
        fields = [
            "id",
            "part",
            "part_code",
            "part_name",
            "part_brand",
            "part_unit",
            "is_serialized",
            "inventory_item",
            "inventory_serial",
            "quantity",
            "serial_number",
            "batch_number",
            "source",
            "source_reference",
            "status",
            "scan_status",
            "installed_at",
            "removed_at",
            "notes",
        ]


class ROAssetComponentEventSerializer(serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    part_name = serializers.CharField(source="part.name", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ROAssetComponentEvent
        fields = [
            "id",
            "component",
            "part",
            "part_code",
            "part_name",
            "action",
            "quantity",
            "serial_number",
            "from_status",
            "to_status",
            "source_reference",
            "actor",
            "actor_name",
            "remarks",
            "metadata",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if obj.actor is None:
            return ""
        return obj.actor.get_full_name() or getattr(obj.actor, "phone", "")


class ROAssetSerializer(serializers.ModelSerializer):
    ro_model_name = serializers.CharField(source="ro_model.model_name", read_only=True)
    customer_name = serializers.CharField(source="current_customer.name", read_only=True)
    components = ROAssetComponentSerializer(many=True, read_only=True)
    component_summary = serializers.SerializerMethodField()

    class Meta:
        model = ROAsset
        fields = [
            "id",
            "asset_id",
            "serial_number",
            "qr_code",
            "status",
            "deployment_type",
            "ro_model",
            "ro_model_name",
            "current_customer",
            "customer_name",
            "purchase_date",
            "purchase_invoice",
            "purchase_price",
            "assigned_at",
            "is_active",
            "created_at",
            "component_summary",
            "components",
        ]
        read_only_fields = ["asset_id", "assigned_at", "created_at"]

    def get_component_summary(self, obj):
        components = list(obj.components.all())
        active = [row for row in components if row.status == "ACTIVE"]
        return {
            "total_records": len(components),
            "active_records": len(active),
            "scan_pending": sum(1 for row in active if row.scan_status == "PENDING"),
            "scan_verified": sum(1 for row in active if row.scan_status == "VERIFIED"),
            "non_scan": sum(1 for row in active if row.scan_status == "NOT_REQUIRED"),
        }


class ROAssetMovementSerializer(serializers.ModelSerializer):
    asset_id = serializers.CharField(source="asset.asset_id", read_only=True)
    serial_number = serializers.CharField(source="asset.serial_number", read_only=True)
    ro_model_name = serializers.CharField(source="asset.ro_model.model_name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ROAssetMovement
        fields = [
            "id",
            "asset",
            "asset_id",
            "serial_number",
            "ro_model_name",
            "action",
            "customer",
            "customer_name",
            "request_id",
            "request_number",
            "from_status",
            "to_status",
            "performed_by",
            "performed_by_name",
            "remarks",
            "created_at",
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by is None:
            return ""
        return obj.performed_by.get_full_name() or getattr(obj.performed_by, "phone", "")
