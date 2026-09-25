from rest_framework import serializers

from .models import Job, JobMedia, JobGPSLog, JobPartUsed, JobSignature
from .services import NO_PARTS_ACTIVITY


class JobPartUsedSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="inventory_item.part.name", read_only=True)
    part_code = serializers.CharField(source="inventory_item.part.code", read_only=True)
    serial_number = serializers.CharField(source="inventory_item.serial_number", read_only=True)
    barcode = serializers.CharField(source="inventory_item.barcode", read_only=True)
    inventory_status = serializers.CharField(source="inventory_item.status", read_only=True)
    engineer_name = serializers.CharField(
        source="inventory_item.bag_item.engineer.user.get_full_name", read_only=True
    )
    engineer_employee_id = serializers.CharField(
        source="inventory_item.bag_item.engineer.employee_id", read_only=True
    )

    class Meta:
        model = JobPartUsed
        fields = [
            "id", "job", "inventory_item", "part_name", "part_code",
            "serial_number", "barcode", "inventory_status", "engineer_name",
            "engineer_employee_id", "quantity", "remarks", "used_at",
        ]
        read_only_fields = [
            "id", "job", "part_name", "part_code", "serial_number", "barcode",
            "inventory_status", "engineer_name", "engineer_employee_id", "used_at",
        ]


class JobSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    address = serializers.CharField(source="customer.address", read_only=True)
    area = serializers.CharField(source="customer.area", read_only=True)
    city = serializers.CharField(source="customer.city", read_only=True)
    latitude = serializers.DecimalField(
        source="customer.latitude", max_digits=10, decimal_places=7, read_only=True
    )
    longitude = serializers.DecimalField(
        source="customer.longitude", max_digits=10, decimal_places=7, read_only=True
    )
    engineer_name = serializers.CharField(source="engineer.user.get_full_name", read_only=True)
    asset_id = serializers.SerializerMethodField()
    parts_used = serializers.SerializerMethodField()
    before_photo_uploaded = serializers.SerializerMethodField()
    after_photo_uploaded = serializers.SerializerMethodField()
    otp_verified = serializers.BooleanField(read_only=True)
    signature_uploaded = serializers.SerializerMethodField()
    parts_decision = serializers.SerializerMethodField()

    def get_asset_id(self, obj):
        if not obj.ro_asset_id:
            return ""
        return obj.ro_asset.asset_id or ""

    def get_parts_used(self, obj):
        return JobPartUsedSerializer(obj.parts_used.all(), many=True, context=self.context).data

    def get_before_photo_uploaded(self, obj):
        return obj.media.filter(media_type="PHOTO", description="Before Photo").exists()

    def get_after_photo_uploaded(self, obj):
        return obj.media.filter(media_type="PHOTO", description="After Photo").exists()

    def get_signature_uploaded(self, obj):
        return hasattr(obj, "signature")

    def get_parts_decision(self, obj):
        if obj.parts_used.exists():
            return "USED"
        if obj.activity_logs.filter(activity=NO_PARTS_ACTIVITY).exists():
            return "NO_PARTS"
        return "PENDING"

    class Meta:
        model = Job
        fields = [
            "id", "job_id", "job_type", "priority", "status", "scheduled_date",
            "customer", "customer_name", "customer_phone", "address", "area", "city",
            "latitude", "longitude", "engineer", "engineer_name", "ro_asset", "asset_id",
            "parts_used", "parts_decision", "before_photo_uploaded", "after_photo_uploaded",
            "otp_verified", "signature_uploaded", "remarks", "assigned_at", "accepted_at",
            "on_the_way_at", "arrived_at", "in_progress_at", "completed_at",
        ]


class JobStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["ACCEPTED", "ON_THE_WAY", "ARRIVED", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    )


class JobMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobMedia
        fields = "__all__"
        read_only_fields = ["id", "job", "uploaded_at"]


class JobGPSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobGPSLog
        fields = "__all__"
        read_only_fields = ["id", "job", "captured_at"]


class JobSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSignature
        fields = "__all__"
        read_only_fields = ["id", "job", "uploaded_at"]
