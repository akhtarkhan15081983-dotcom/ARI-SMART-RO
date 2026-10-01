from . import serializers as base_serializers


class HardenedCustomerProfileSerializer(base_serializers.CustomerProfileSerializer):
    """Customer self-service may edit contact/profile data, not RO operations."""

    class Meta(base_serializers.CustomerProfileSerializer.Meta):
        read_only_fields = list(base_serializers.CustomerProfileSerializer.Meta.read_only_fields) + [
            "ro_model",
            "is_active",
        ]
