from django.contrib import admin
from assets.models import ROAsset


@admin.register(ROAsset)
class ROAssetAdmin(admin.ModelAdmin):

    list_display = (
        "asset_id",
        "ro_model",
        "status",
        "current_customer",
        "is_active",
    )

    list_filter = (
        "status",
        "ro_model",
    )

    search_fields = (
        "asset_id",
        "serial_number",
    )

    readonly_fields = (
        "asset_id",
        "created_at",
    )