from rest_framework import serializers

from .models.asset import ROAlarm, ROAsset


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
            "next_filter_change_date",
            "output_tds_attention_level",
            "alarm_monitoring_enabled",
        ]


class ROAlarmAssetSerializer(serializers.ModelSerializer):
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
            "status",
            "ro_model_name",
            "customer_name",
            "next_filter_change_date",
            "output_tds_attention_level",
            "alarm_monitoring_enabled",
        ]
        read_only_fields = [
            "id",
            "asset_id",
            "serial_number",
            "status",
            "ro_model_name",
            "customer_name",
        ]


class ROAlarmSerializer(serializers.ModelSerializer):
    asset_id = serializers.CharField(source="ro_asset.asset_id", read_only=True)
    ro_model_name = serializers.CharField(
        source="ro_asset.ro_model.model_name",
        read_only=True,
    )
    customer_name = serializers.CharField(
        source="ro_asset.current_customer.name",
        read_only=True,
    )
    alarm_type_label = serializers.CharField(
        source="get_alarm_type_display",
        read_only=True,
    )
    severity_label = serializers.CharField(
        source="get_severity_display",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    source_label = serializers.CharField(
        source="get_source_display",
        read_only=True,
    )

    class Meta:
        model = ROAlarm
        fields = [
            "id",
            "ro_asset",
            "asset_id",
            "ro_model_name",
            "customer_name",
            "alarm_type",
            "alarm_type_label",
            "severity",
            "severity_label",
            "status",
            "status_label",
            "source",
            "source_label",
            "title",
            "message",
            "observed_value",
            "due_date",
            "acknowledged_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
