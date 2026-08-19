from rest_framework import serializers

from .models import (
    Job,
    JobMedia,
    JobGPSLog,
    JobPartUsed,
    JobSignature,
)


# ============================================================
# JOB PART USED
# ============================================================

class JobPartUsedSerializer(serializers.ModelSerializer):

    # Part details
    part_name = serializers.CharField(
        source="inventory_item.part.name",
        read_only=True,
    )

    part_code = serializers.CharField(
        source="inventory_item.part.code",
        read_only=True,
    )

    # Physical inventory item
    serial_number = serializers.CharField(
        source="inventory_item.serial_number",
        read_only=True,
    )

    barcode = serializers.CharField(
        source="inventory_item.barcode",
        read_only=True,
    )

    inventory_status = serializers.CharField(
        source="inventory_item.status",
        read_only=True,
    )

    # Engineer who currently owns / used the item
    engineer_name = serializers.CharField(
        source="inventory_item.bag_item.engineer.user.get_full_name",
        read_only=True,
    )

    engineer_employee_id = serializers.CharField(
        source="inventory_item.bag_item.engineer.employee_id",
        read_only=True,
    )

    class Meta:
        model = JobPartUsed

        fields = [
            "id",

            # Job
            "job",

            # Inventory
            "inventory_item",
            "part_name",
            "part_code",
            "serial_number",
            "barcode",
            "inventory_status",

            # Engineer
            "engineer_name",
            "engineer_employee_id",

            # Usage
            "quantity",
            "remarks",
            "used_at",
        ]

        read_only_fields = [
            "id",
            "job",
            "part_name",
            "part_code",
            "serial_number",
            "barcode",
            "inventory_status",
            "engineer_name",
            "engineer_employee_id",
            "used_at",
        ]


# ============================================================
# JOB
# ============================================================

class JobSerializer(serializers.ModelSerializer):

    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
    )

    customer_phone = serializers.CharField(
        source="customer.phone",
        read_only=True,
    )

    address = serializers.CharField(
        source="customer.address",
        read_only=True,
    )

    area = serializers.CharField(
        source="customer.area",
        read_only=True,
    )

    city = serializers.CharField(
        source="customer.city",
        read_only=True,
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
        read_only=True,
    )

    asset_id = serializers.CharField(
        source="ro_asset.asset_id",
        read_only=True,
    )

    # ========================================================
    # PARTS USED
    # ========================================================

    parts_used = serializers.SerializerMethodField()

    def get_parts_used(self, obj):

        return JobPartUsedSerializer(
            obj.parts_used.all(),
            many=True,
            context=self.context,
        ).data

    # ========================================================
    # META
    # ========================================================

    class Meta:
        model = Job

        fields = [
            # ------------------------------------------------
            # BASIC
            # ------------------------------------------------

            "id",
            "job_id",
            "job_type",
            "priority",
            "status",
            "scheduled_date",

            # ------------------------------------------------
            # CUSTOMER
            # ------------------------------------------------

            "customer",
            "customer_name",
            "customer_phone",

            "address",
            "area",
            "city",

            "latitude",
            "longitude",

            # ------------------------------------------------
            # ENGINEER
            # ------------------------------------------------

            "engineer",
            "engineer_name",

            # ------------------------------------------------
            # ASSET
            # ------------------------------------------------

            "ro_asset",
            "asset_id",

            # ------------------------------------------------
            # PARTS
            # ------------------------------------------------

            "parts_used",

            # ------------------------------------------------
            # REMARKS
            # ------------------------------------------------

            "remarks",

            # ------------------------------------------------
            # STATUS TIMESTAMPS
            # ------------------------------------------------

            "assigned_at",
            "accepted_at",
            "on_the_way_at",
            "arrived_at",
            "in_progress_at",
            "completed_at",
        ]


# ============================================================
# JOB STATUS
# ============================================================

class JobStatusSerializer(
    serializers.Serializer
):

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


# ============================================================
# JOB MEDIA
# ============================================================

class JobMediaSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = JobMedia

        fields = "__all__"

        read_only_fields = [
            "id",
            "job",
            "uploaded_at",
        ]


# ============================================================
# JOB GPS
# ============================================================

class JobGPSLogSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = JobGPSLog

        fields = "__all__"

        read_only_fields = [
            "id",
            "job",
            "captured_at",
        ]


# ============================================================
# JOB SIGNATURE
# ============================================================

class JobSignatureSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = JobSignature

        fields = "__all__"

        read_only_fields = [
            "id",
            "job",
            "uploaded_at",
        ]