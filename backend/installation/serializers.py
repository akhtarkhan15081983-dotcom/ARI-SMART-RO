from rest_framework import serializers
from .models import InstallationPart,Installation
from inventory.models import InventoryItem


class InstallationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Installation
        fields = [
            "id",
            "installation_id",
            "customer",
            "engineer",
            "ro_asset",
            "business_type",
            "scheduled_date",
            "completed_date",
            "status",
            "remarks",

            "input_tds",
            "output_tds",
            "latitude",
            "longitude",
            "referral_name",
        ]


class InstallationPartSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstallationPart
        fields = "__all__"

    def validate_inventory_item(self, value):
        if value.status != "ISSUED":
            raise serializers.ValidationError(
                "This part is not issued to an engineer."
            )
        return value

    def create(self, validated_data):
        installation_part = super().create(validated_data)

        inventory_item = installation_part.inventory_item
        inventory_item.status = "INSTALLED"
        inventory_item.save()

        return installation_part