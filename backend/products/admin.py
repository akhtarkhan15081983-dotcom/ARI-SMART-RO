from django.contrib import admin

from .models import (
    ProductCategory,
    ROModel,
    ROModelPart,
    ROModelImage,
)


class ROModelImageInline(admin.TabularInline):
    model = ROModelImage
    extra = 1
    fields = ("image", "alt_text", "sort_order")


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "is_active",
    )

    search_fields = (
        "name",
    )

    list_filter = (
        "is_active",
    )


@admin.register(ROModel)
class ROModelAdmin(admin.ModelAdmin):

    inlines = [ROModelImageInline]

    list_display = (
        "id",
        "model_name",
        "category",
        "business_type",
        "monthly_rent",
        "selling_price",
        "stock_quantity",
        "is_active",
    )

    search_fields = (
        "model_name",
    )

    list_filter = (
        "category",
        "business_type",
        "is_active",
    )


@admin.register(ROModelPart)
class ROModelPartAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "ro_model",
        "part",
        "quantity",
        "is_mandatory",
    )

    search_fields = (
        "ro_model__model_name",
        "part__name",
    )

    list_filter = (
        "is_mandatory",
    )
