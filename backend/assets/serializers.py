from rest_framework import serializers

from .models.asset import ROAsset


class ROAssetSerializer(serializers.ModelSerializer):

    ro_model_name = serializers.CharField(
        source="ro_model.model_name",
        read_only=True,
    )

    customer_name = serializers.CharField(
        source="current_customer.name",
        read_only=True,
    )

    class Meta:
        model = ROAsset

        fields = [
            "id",
            "asset_id",
            "serial_number",
            "qr_code",
            "status",
            "ro_model",
            "ro_model_name",
            "current_customer",
            "customer_name",
            "purchase_date",
        ]