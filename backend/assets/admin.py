from django.contrib import admin

from .models import ROAsset, ROAssetMovement


@admin.register(ROAsset)
class ROAssetAdmin(admin.ModelAdmin):
    list_display = (
        "asset_id",
        "serial_number",
        "ro_model",
        "status",
        "deployment_type",
        "current_customer",
        "purchase_invoice",
        "purchase_price",
        "purchase_date",
        "is_active",
    )
    list_filter = ("status", "deployment_type", "ro_model", "is_active")
    search_fields = (
        "asset_id",
        "serial_number",
        "ro_model__model_name",
        "current_customer__name",
        "current_customer__phone",
        "purchase_invoice",
    )
    autocomplete_fields = ("ro_model", "current_customer")
    readonly_fields = ("asset_id", "assigned_at", "created_at")
    ordering = ("-id",)


@admin.register(ROAssetMovement)
class ROAssetMovementAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "action",
        "customer",
        "from_status",
        "to_status",
        "request_number",
        "performed_by",
        "created_at",
    )
    list_filter = ("action", "from_status", "to_status", "created_at")
    search_fields = (
        "asset__asset_id",
        "asset__serial_number",
        "customer__name",
        "request_number",
        "remarks",
    )
    readonly_fields = (
        "asset",
        "action",
        "customer",
        "request_id",
        "request_number",
        "from_status",
        "to_status",
        "performed_by",
        "remarks",
        "created_at",
    )
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
