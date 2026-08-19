from rest_framework import serializers
from .models import InstallationPart,Installation
from inventory.models import InventoryItem


class InstallationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Installation
        fields = [
            "id",
            "installation_id",
            "job",
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
        extra_kwargs = {
            "job": {"required": False},
            "customer": {"required": False},
            "engineer": {"required": False},
            "ro_asset": {"required": False},
            "scheduled_date": {"required": False},
            "business_type": {"required": False},
            "status": {"required": False},
            "completed_date": {"required": False},
        }


class InstallationPartSerializer(serializers.ModelSerializer):

    class Meta:
        model = InstallationPart
        fields = "__all__"

    def validate_inventory_item(self, value):

        if value.status not in ["ISSUED", "INSTALLED"]:
            raise serializers.ValidationError(
                "Invalid inventory item."
            )

        return value

    def create(self, validated_data):

        installation_part = super().create(validated_data)

        inventory_item = installation_part.inventory_item

        if (
            inventory_item
            and inventory_item.status != "INSTALLED"
        ):
            inventory_item.status = "INSTALLED"
            inventory_item.save()

        return installation_part