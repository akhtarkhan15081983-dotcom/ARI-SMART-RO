from rest_framework import serializers

from .models import Customer


# ============================================================
# CUSTOMER SERIALIZER
# ============================================================

class CustomerSerializer(serializers.ModelSerializer):

    # ----------------------------------------------------------
    # RO MODEL NAME
    # ----------------------------------------------------------
    #
    # Customer model me ro_model abhi CharField hai.
    # Isliye kisi model_name relation ko access nahi karenge.
    #

    ro_model_name = serializers.CharField(
        source="ro_model",
        read_only=True,
    )

    # ----------------------------------------------------------
    # ENGINEER NAME
    # ----------------------------------------------------------

    engineer_name = serializers.CharField(
        source="assigned_engineer.user.get_full_name",
        read_only=True,
        default="",
    )

    class Meta:

        model = Customer

        fields = [

            "id",

            "customer_id",

            "card_number",

            "old_card_number",

            "name",

            "phone",

            "alternate_phone",

            "email",

            "gender",

            "address",

            "area",

            "city",

            "state",

            "pincode",

            "latitude",

            "longitude",

            "ro_model",

            "ro_model_name",

            "installation_charge",

            "monthly_rent",

            "security_deposit",

            "installation_date",

            "assigned_engineer",

            "engineer_name",

            "is_active",
        ]


# ============================================================
# WALK-IN CUSTOMER SERIALIZER
# ============================================================

class WalkInCustomerSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = Customer

        fields = [

            "id",

            "customer_id",

            "card_number",

            "name",

            "phone",

            "alternate_phone",

            "address",

            "area",

            "city",

            "state",

            "pincode",

            "latitude",

            "longitude",

            "ro_model",

            "installation_charge",

            "monthly_rent",

            "security_deposit",
        ]

        read_only_fields = [

            "id",

            "customer_id",

            "card_number",
        ]

# ============================================================
# CUSTOMER APP PROFILE SERIALIZER
# ============================================================

class CustomerProfileSerializer(
    serializers.ModelSerializer
):

    customer_id = serializers.CharField(
        read_only=True
    )

    card_number = serializers.CharField(
        read_only=True
    )

    phone = serializers.CharField(
        read_only=True
    )

    installation_charge = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    monthly_rent = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    security_deposit = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    installation_date = serializers.DateField(
        read_only=True
    )

    assigned_engineer = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:

        model = Customer

        fields = [

            "id",

            "customer_id",

            "card_number",

            "name",

            "phone",

            "alternate_phone",

            "email",

            "gender",

            "address",

            "area",

            "city",

            "state",

            "pincode",

            "latitude",

            "longitude",

            "ro_model",

            "installation_charge",

            "monthly_rent",

            "security_deposit",

            "installation_date",

            "assigned_engineer",

            "is_active",
        ]

        read_only_fields = [

            "id",

            "customer_id",

            "card_number",

            "phone",

            "installation_charge",

            "monthly_rent",

            "security_deposit",

            "installation_date",

            "assigned_engineer",
        ]

# ============================================================
# CUSTOMER APP - MY RO SERIALIZER
# ============================================================

from assets.models.asset import ROAsset


class MyROSerializer(serializers.ModelSerializer):

    ro_model_name = serializers.CharField(
        source="ro_model.model_name",
        read_only=True,
    )

    ro_model_id = serializers.IntegerField(
        source="ro_model.id",
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

            "ro_model_id",

            "ro_model_name",

            "purchase_date",

        ]

        read_only_fields = fields