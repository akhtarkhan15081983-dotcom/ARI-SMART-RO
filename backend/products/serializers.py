from rest_framework import serializers

from .models import (
    ProductCategory,
    ROModel,
    ROModelPart,
)


class ProductCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductCategory
        fields = "__all__"


class ROModelSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:
        model = ROModel
        fields = "__all__"


class ROModelPartSerializer(serializers.ModelSerializer):

    part_name = serializers.CharField(
        source="part.name",
        read_only=True,
    )

    ro_model_name = serializers.CharField(
        source="ro_model.model_name",
        read_only=True,
    )

    class Meta:
        model = ROModelPart
        fields = "__all__"