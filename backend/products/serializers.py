from rest_framework import serializers

from .models import (
    ProductCategory,
    ROModel,
    ROModelPart,
    ROModelImage,
)


class ROModelImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ROModelImage
        fields = ["id", "image_url", "alt_text", "sort_order"]

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ProductCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductCategory
        fields = "__all__"


class ROModelSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    images = ROModelImageSerializer(many=True, read_only=True)

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
