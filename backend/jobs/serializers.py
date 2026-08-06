from rest_framework import serializers

from .models import Job, JobMedia,JobGPSLog,JobPartUsed,JobSignature


class JobSerializer(serializers.ModelSerializer):

    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True
    )

    customer_phone = serializers.CharField(
        source="customer.phone",
        read_only=True,
    )

    address = serializers.CharField(
        source="customer.address",
        read_only=True
    )

    area = serializers.CharField(
        source="customer.area",
        read_only=True
    )

    city = serializers.CharField(
        source="customer.city",
        read_only=True
    )

    latitude = serializers.DecimalField(
        source="customer.latitude",
        max_digits=10,
        decimal_places=7,
        read_only=True,
    )

    longitude = serializers.DecimalField(
        source="customer.longitude",
        max_digits=10,
        decimal_places=7,
        read_only=True,
    )

    engineer_name = serializers.CharField(
        source="engineer.user.get_full_name",
        read_only=True
    )

    asset_id = serializers.CharField(
        source="ro_asset.asset_id",
        read_only=True
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "job_id",
            "job_type",
            "priority",
            "status",
            "scheduled_date",
            "customer",
            "customer_name",
            "customer_phone",
            "address",
            "area",
            "city",
            "latitude",
            "longitude",
            "engineer",
            "engineer_name",
            "ro_asset",
            "asset_id",
            "remarks",
            "assigned_at",
            "accepted_at",
            "on_the_way_at",
            "arrived_at",
            "in_progress_at",
            "completed_at",
        ]

class JobStatusSerializer(serializers.Serializer):

    status = serializers.ChoiceField(
        choices=[
            "ACCEPTED",
            "ON_THE_WAY",
            "ARRIVED",
            "IN_PROGRESS",
            "COMPLETED",
            "CANCELLED",
        ]
    )

class JobMediaSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobMedia
        fields = "__all__"
        read_only_fields = [
            "id",
            "job",
            "uploaded_at",
        ]

class JobGPSLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobGPSLog
        fields = "__all__"
        read_only_fields = [
            "id",
            "job",
            "captured_at",
        ]

class JobPartUsedSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobPartUsed
        fields = "__all__"
        read_only_fields = [
            "id",
            "job",
            "used_at",
        ]

class JobSignatureSerializer(serializers.ModelSerializer):

    class Meta:
        model = JobSignature
        fields = "__all__"

        read_only_fields = [
            "id",
            "job",
            "uploaded_at",
        ]