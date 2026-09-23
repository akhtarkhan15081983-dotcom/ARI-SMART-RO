from rest_framework import serializers

from accounts.offers import best_public_offer
from .models import Customer, PublicCustomerRequest


class PublicCustomerRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.model_name", read_only=True)
    offer_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = PublicCustomerRequest
        fields = [
            "id", "request_number", "request_type", "product", "product_name",
            "plan_name", "customer_name", "phone", "alternate_phone", "email",
            "address", "city", "state", "pincode", "quantity", "unit_price",
            "base_amount", "discount_amount", "total_amount", "offer_code",
            "payment_method", "preferred_date", "referral_code",
            "notes", "status", "created_at",
        ]
        read_only_fields = [
            "id", "request_number", "product_name", "unit_price", "base_amount",
            "discount_amount", "total_amount", "status", "created_at",
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
        offer_code = validated_data.pop("offer_code", "")
        if product is not None:
            unit_price = product.monthly_rent if request_type == "RENTAL" else product.selling_price
            base_amount = unit_price * quantity
            validated_data["unit_price"] = unit_price
            validated_data["base_amount"] = base_amount

            scope = "PURCHASE" if request_type == "PURCHASE" else "RENT"
            offer, discount, final_amount = best_public_offer(
                scope,
                base_amount,
                promo_code=offer_code,
            )
            if offer_code and offer is None:
                raise serializers.ValidationError({
                    "offer_code": "This promo code is invalid, expired or not applicable."
                })
            validated_data["discount_amount"] = discount
            validated_data["total_amount"] = final_amount
            validated_data["applied_offer"] = offer
            validated_data.setdefault("plan_name", product.model_name)
        return super().create(validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    ro_model_name = serializers.CharField(source="ro_model", read_only=True)
    engineer_name = serializers.CharField(
        source="assigned_engineer.user.get_full_name",
        read_only=True,
        default="",
    )
    qr_payload = serializers.SerializerMethodField()

    def get_qr_payload(self, obj):
        return f"ARI-SMART-RO:CUSTOMER:{obj.customer_id}"

    class Meta:
        model = Customer
        fields = [
            "id", "customer_id", "card_number", "old_card_number", "name", "phone",
            "alternate_phone", "email", "gender", "address", "area", "city", "state",
            "pincode", "latitude", "longitude", "ro_model", "ro_model_name",
            "installation_charge", "monthly_rent", "security_deposit", "ownership_type",
            "rent_to_purchase_date", "rent_to_purchase_amount", "rent_at_conversion",
            "security_adjusted_at_conversion", "rent_to_purchase_notes", "deactivated_at",
            "deactivation_reason", "installation_date", "assigned_engineer", "engineer_name",
            "qr_payload", "is_active",
        ]
        read_only_fields = [
            "id", "customer_id", "card_number", "assigned_engineer", "engineer_name",
            "qr_payload", "is_active", "deactivated_at", "deactivation_reason",
            "ownership_type", "rent_to_purchase_date", "rent_to_purchase_amount",
            "rent_at_conversion", "security_adjusted_at_conversion", "rent_to_purchase_notes",
        ]


class WalkInCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "customer_id", "card_number", "name", "phone", "alternate_phone",
            "address", "area", "city", "state", "pincode", "latitude", "longitude",
            "ro_model", "installation_charge", "monthly_rent", "security_deposit",
        ]
        read_only_fields = ["id", "customer_id", "card_number"]


class CustomerProfileSerializer(serializers.ModelSerializer):
    customer_id = serializers.CharField(read_only=True)
    card_number = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)
    installation_charge = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    monthly_rent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    security_deposit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    installation_date = serializers.DateField(read_only=True)
    assigned_engineer = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "customer_id", "card_number", "name", "phone", "alternate_phone",
            "email", "gender", "address", "area", "city", "state", "pincode",
            "latitude", "longitude", "ro_model", "installation_charge", "monthly_rent",
            "security_deposit", "installation_date", "assigned_engineer", "is_active",
        ]
        read_only_fields = [
            "id", "customer_id", "card_number", "phone", "installation_charge",
            "monthly_rent", "security_deposit", "installation_date", "assigned_engineer",
        ]


from assets.models.asset import ROAsset
from assets.serializers import ROAssetComponentSerializer


class MyROSerializer(serializers.ModelSerializer):
    ro_model_name = serializers.CharField(source="ro_model.model_name", read_only=True)
    ro_model_id = serializers.IntegerField(source="ro_model.id", read_only=True)
    components = ROAssetComponentSerializer(many=True, read_only=True)
    component_summary = serializers.SerializerMethodField()

    class Meta:
        model = ROAsset
        fields = [
            "id", "asset_id", "serial_number", "qr_code", "status", "deployment_type",
            "ro_model_id", "ro_model_name", "purchase_date", "assigned_at",
            "component_summary", "components",
        ]
        read_only_fields = fields

    def get_component_summary(self, obj):
        rows = list(obj.components.all())
        active = [row for row in rows if row.status == "ACTIVE"]
        return {
            "active_parts": len(active),
            "scan_required": sum(1 for row in active if row.scan_status in {"PENDING", "VERIFIED"}),
            "scan_pending": sum(1 for row in active if row.scan_status == "PENDING"),
            "scan_verified": sum(1 for row in active if row.scan_status == "VERIFIED"),
            "non_scan": sum(1 for row in active if row.scan_status == "NOT_REQUIRED"),
            "history_records": len(rows) - len(active),
        }
