from rest_framework import serializers
from .models import EngineerBagItem
from employees.models import EmployeeProfile
from .models import InventoryItem

class EngineerBagIssueSerializer(serializers.ModelSerializer):

    class Meta:
        model = EngineerBagItem
        fields = [
            "id",
            "engineer",
            "inventory_item",
            "status",
            "issue_date",
            "remarks",
        ]
        read_only_fields = [
            "status",
            "issue_date",
        ]
    

    def validate(self, attrs):

        inventory_item = attrs["inventory_item"]

        if inventory_item.status != "IN_STOCK":
            raise serializers.ValidationError(
                "This part is not available in stock."
            )

        if inventory_item.part.is_serialized:

            if not inventory_item.serial_number:
                raise serializers.ValidationError(
                    "Serialized part must have a serial number."
                )
        if EngineerBagItem.objects.filter(
            inventory_item=inventory_item,
            status="ISSUED"
        ).exists():
            raise serializers.ValidationError(
                "This part is already issued to an engineer."
            )
        return attrs

class OCRVerifySerializer(serializers.Serializer):

    engineer = serializers.PrimaryKeyRelatedField(
        queryset=EmployeeProfile.objects.all()
    )

    serial_number = serializers.CharField(max_length=50)

class MyBagSerializer(serializers.ModelSerializer):

    part_name = serializers.CharField(
        source="inventory_item.part.name",
        read_only=True,
    )

    serial_number = serializers.CharField(
        source="inventory_item.serial_number",
        read_only=True,
    )

    class Meta:
        model = EngineerBagItem
        fields = [
            "id",
            "part_name",
            "serial_number",
            "status",
        ]
