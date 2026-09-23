from django.utils import timezone
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
    warranty_months = serializers.IntegerField(source="part.warranty_months", read_only=True)
    replacement_interval_days = serializers.IntegerField(source="part.replacement_interval_days", read_only=True)
    inventory_serial = serializers.CharField(source="inventory_item.serial_number", read_only=True, default="")
    warranty_end_date = serializers.SerializerMethodField()
    warranty_status = serializers.SerializerMethodField()
    replacement_due_date = serializers.SerializerMethodField()
    replacement_status = serializers.SerializerMethodField()

    class Meta:
        model = ROAssetComponent
        fields = [
            "id", "part", "part_code", "part_name", "part_brand", "part_unit",
            "is_serialized", "warranty_months", "replacement_interval_days",
            "inventory_item", "inventory_serial", "quantity", "serial_number",
            "batch_number", "source", "source_reference", "status", "scan_status",
            "installed_at", "removed_at", "warranty_end_date", "warranty_status",
            "replacement_due_date", "replacement_status", "notes",
        ]

    def get_warranty_end_date(self, obj):
        value = obj.warranty_end_date
        return value.isoformat() if value else None

    def get_warranty_status(self, obj):
        value = obj.warranty_end_date
        if value is None:
            return "NO_WARRANTY"
        return "IN_WARRANTY" if value >= timezone.localdate() else "EXPIRED"

    def get_replacement_due_date(self, obj):
        value = obj.replacement_due_date
        return value.isoformat() if value else None

    def get_replacement_status(self, obj):
        value = obj.replacement_due_date
        if value is None:
            return "NOT_SCHEDULED"
        today = timezone.localdate()
        if value < today:
            return "OVERDUE"
        if value <= today + timezone.timedelta(days=30):
            return "DUE_SOON"
        return "OK"


class ROAssetComponentEventSerializer(serializers.ModelSerializer):
    part_code = serializers.CharField(source="part.code", read_only=True)
    part_name = serializers.CharField(source="part.name", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = ROAssetComponentEvent
        fields = [
            "id", "component", "part", "part_code", "part_name", "action",
            "quantity", "serial_number", "from_status", "to_status",
            "source_reference", "actor", "actor_name", "remarks", "metadata", "created_at",
        ]

    def get_actor_name(self, obj):
        if obj.actor is None:
            return ""
        return obj.actor.get_full_name() or getattr(obj.actor, "phone", "")


class ROAssetSerializer(serializers.ModelSerializer):
    ro_model_name = serializers.CharField(source="ro_model.model_name", read_only=True)
    customer_name = serializers.CharField(source="current_customer.name", read_only=True)
    reserved_customer_name = serializers.CharField(source="reserved_for_customer.name", read_only=True, default="")
    components = ROAssetComponentSerializer(many=True, read_only=True)
    component_summary = serializers.SerializerMethodField()
    bom_verified = serializers.BooleanField(read_only=True)
    release_ready = serializers.BooleanField(read_only=True)
    reservation_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ROAsset
        fields = [
            "id", "asset_id", "serial_number", "qr_code", "status", "deployment_type",
            "ro_model", "ro_model_name", "current_customer", "customer_name",
            "purchase_date", "purchase_invoice", "purchase_price", "assigned_at",
            "qc_status", "qc_checked_at", "qc_notes", "cleaned_at", "sanitized_at",
            "reserved_for_customer", "reserved_customer_name", "reserved_at",
            "reservation_expires_at", "reservation_active", "bom_verified",
            "release_ready", "is_active", "created_at", "component_summary", "components",
        ]
        read_only_fields = [
            "asset_id", "assigned_at", "created_at", "qc_checked_at", "reservation_active",
            "bom_verified", "release_ready",
        ]

    def get_component_summary(self, obj):
        components = list(obj.components.all())
        active = [row for row in components if row.status == "ACTIVE"]
        return {
            "total_records": len(components),
            "active_records": len(active),
            "scan_pending": sum(1 for row in active if row.scan_status == "PENDING"),
            "scan_verified": sum(1 for row in active if row.scan_status == "VERIFIED"),
            "non_scan": sum(1 for row in active if row.scan_status == "NOT_REQUIRED"),
            "replacement_due_soon": sum(
                1 for row in active
                if row.replacement_due_date is not None
                and timezone.localdate() <= row.replacement_due_date <= timezone.localdate() + timezone.timedelta(days=30)
            ),
            "replacement_overdue": sum(
                1 for row in active
                if row.replacement_due_date is not None and row.replacement_due_date < timezone.localdate()
            ),
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
            "id", "asset", "asset_id", "serial_number", "ro_model_name", "action",
            "customer", "customer_name", "request_id", "request_number", "from_status",
            "to_status", "performed_by", "performed_by_name", "remarks", "created_at",
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by is None:
            return ""
        return obj.performed_by.get_full_name() or getattr(obj.performed_by, "phone", "")
