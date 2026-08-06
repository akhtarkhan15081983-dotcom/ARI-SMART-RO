from django.contrib import admin
from .models import PartCategory, PartMaster


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(PartMaster)
class PartMasterAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "brand",
        "unit",
        "warranty_months",
        "is_active",
    )

    list_filter = (
        "category",
        "brand",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "brand",
    )