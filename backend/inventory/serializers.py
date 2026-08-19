from rest_framework import serializers

from .models import (
    EngineerBagItem,
    InventoryItem,
    InventoryAuditLog,
    PartRequest,
)

from employees.models import EmployeeProfile
from partmaster.models import PartMaster


class EngineerBagIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = EngineerBagItem
        fields = ["id", "engineer", "inventory_item", "status", "issue_date", "remarks"]
        read_only_fields = ["status", "issue_date"]

    def validate(self, attrs):
        inventory_item = attrs["inventory_item"]
        if inventory_item.status != "IN_STOCK":
            raise serializers.ValidationError({"inventory_item": "This part is not available in stock."})
        if inventory_item.part.is_serialized and not inventory_item.serial_number:
            raise serializers.ValidationError({"inventory_item": "Serialized part must have a serial number."})
        if EngineerBagItem.objects.filter(inventory_item=inventory_item, status="ISSUED").exists():
            raise serializers.ValidationError({"inventory_item": "This physical part is already issued to an engineer."})
        engineer = attrs["engineer"]
        if hasattr(engineer, "is_active") and not engineer.is_active:
            raise serializers.ValidationError({"engineer": "This engineer is inactive."})
        return attrs


class OCRVerifySerializer(serializers.Serializer):
    engineer = serializers.PrimaryKeyRelatedField(queryset=EmployeeProfile.objects.all())
    serial_number = serializers.CharField(max_length=50)


class MyBagSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="inventory_item.part.name", read_only=True)
    part_code = serializers.CharField(source="inventory_item.part.code", read_only=True)
    serial_number = serializers.CharField(source="inventory_item.serial_number", read_only=True)
    barcode = serializers.CharField(source="inventory_item.barcode", read_only=True)

    class Meta:
        model = EngineerBagItem
        fields = ["id", "part_name", "part_code", "serial_number", "barcode", "status", "issue_date", "install_date", "return_date", "remarks"]


class InventoryAuditLogSerializer(serializers.ModelSerializer):
    engineer_name = serializers.CharField(source="engineer.user.get_full_name", read_only=True)

    class Meta:
        model = InventoryAuditLog
        fields = ["id", "inventory_item", "engineer", "engineer_name", "performed_by", "job", "action", "old_status", "new_status", "serial_number", "remarks", "created_at"]
        read_only_fields = fields


class PartRequestSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    part_code = serializers.CharField(source="part.code", read_only=True)

    class Meta:
        model = PartRequest
        fields = [
            "id", "part", "part_name", "part_code", "quantity", "remarks",
            "status", "review_remarks", "created_at", "reviewed_at",
        ]
        read_only_fields = ["status", "review_remarks", "created_at", "reviewed_at"]

    def validate_part(self, part):
        if not part.is_active:
            raise serializers.ValidationError("Inactive parts cannot be requested.")
        return part

    def validate_quantity(self, quantity):
        if quantity < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return quantity


class PartCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartMaster
        fields = ["id", "name", "code", "unit"]
