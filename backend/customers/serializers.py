from rest_framework import serializers

from .models import Customer, PublicCustomerRequest


class PublicCustomerRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.model_name", read_only=True)

    class Meta:
        model = PublicCustomerRequest
        fields = [
            "id", "request_number", "request_type", "product", "product_name",
            "plan_name", "customer_name", "phone", "alternate_phone", "email",
            "address", "city", "state", "pincode", "quantity", "unit_price",
            "total_amount", "payment_method", "preferred_date", "referral_code",
            "notes", "status", "created_at",
        ]
        read_only_fields = [
            "id", "request_number", "product_name", "unit_price", "total_amount",
            "status", "created_at",
        ]

    def validate_phone(self, value):
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) != 10 or digits[0] not in "6789":
            raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return digits

    def validate_pincode(self, value):
        if len(value) != 6 or not value.isdigit():
            raise serializers.ValidationError("Enter a valid 6-digit pincode.")
        return value

    def validate(self, attrs):
        request_type = attrs.get("request_type")
        product = attrs.get("product")
        if request_type == "PURCHASE" and product is None:
            raise serializers.ValidationError({"product": "Select a product."})
        if product is not None and not product.is_active:
            raise serializers.ValidationError({"product": "This product is not currently available."})
        if request_type == "PURCHASE" and product and not product.available_for_sale:
            raise serializers.ValidationError({"product": "This product is not available for sale."})
        if request_type == "RENTAL" and product and not product.available_for_rent:
            raise serializers.ValidationError({"product": "This product is not available for rent."})
        if request_type == "PURCHASE" and product and product.stock_quantity < attrs.get("quantity", 1):
            raise serializers.ValidationError({"quantity": "Requested quantity is not in stock."})
        return attrs

    def create(self, validated_data):
        product = validated_data.get("product")
        quantity = validated_data.get("quantity", 1)
        request_type = validated_data["request_type"]
        if product is not None:
            unit_price = product.monthly_rent if request_type == "RENTAL" else product.selling_price
            validated_data["unit_price"] = unit_price
            validated_data["total_amount"] = unit_price * quantity
            validated_data.setdefault("plan_name", product.model_name)
        return super().create(validated_data)


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
