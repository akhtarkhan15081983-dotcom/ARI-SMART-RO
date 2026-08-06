from rest_framework import serializers
from .models import PartCategory, PartMaster


class PartCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = PartCategory
        fields = "__all__"


class PartMasterSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    class Meta:
        model = PartMaster
        fields = "__all__"