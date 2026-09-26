from rest_framework import serializers

from .models import Customer


class CustomerStaffEditSerializer(serializers.ModelSerializer):
    """Staff-only customer master editor.

    Customer ID and the current/new ARI card number are immutable identifiers.
    All operational customer fields may be corrected through this serializer.
    Internal account linkage/import audit metadata remain system-managed.
    """

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
            "installation_charge",
            "monthly_rent",
            "security_deposit",
            "ownership_type",
            "rent_to_purchase_date",
            "rent_to_purchase_amount",
            "rent_at_conversion",
            "security_adjusted_at_conversion",
            "rent_to_purchase_notes",
            "installation_date",
            "assigned_engineer",
            "is_active",
            "deactivated_at",
            "deactivation_reason",
        ]
        read_only_fields = [
            "id",
            "customer_id",
            "card_number",
        ]

    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value
