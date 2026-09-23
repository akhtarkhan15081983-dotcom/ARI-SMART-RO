from rest_framework import serializers

from .models import ROAsset, ROAssetMovement


class ROAssetSerializer(serializers.ModelSerializer):
    ro_model_name = serializers.CharField(source="ro_model.model_name", read_only=True)
    customer_name = serializers.CharField(source="current_customer.name", read_only=True)

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
        ]
        read_only_fields = ["asset_id", "assigned_at", "created_at"]


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
