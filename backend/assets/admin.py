from django.contrib import admin

from .models import (
    ROAsset,
    ROAssetComponent,
    ROAssetComponentEvent,
    ROAssetMovement,
    ROStockAudit,
    ROStockAuditItem,
)


class ROAssetComponentInline(admin.TabularInline):
    model = ROAssetComponent
    extra = 0
    fields = (
        "part", "quantity", "serial_number", "source", "status",
        "scan_status", "installed_at", "removed_at",
    )
    readonly_fields = ("source", "installed_at", "removed_at")


@admin.register(ROAsset)
class ROAssetAdmin(admin.ModelAdmin):
    list_display = (
        "asset_id", "serial_number", "ro_model", "status", "qc_status",
        "release_ready_flag", "deployment_type", "current_customer",
        "reserved_for_customer", "purchase_invoice", "is_active",
    )
    list_filter = (
        "status", "qc_status", "deployment_type", "ro_model", "is_active",
    )
    search_fields = (
        "asset_id", "serial_number", "ro_model__model_name",
        "current_customer__name", "current_customer__phone",
        "reserved_for_customer__name", "purchase_invoice",
    )
    autocomplete_fields = (
        "ro_model", "current_customer", "reserved_for_customer", "qc_checked_by",
    )
    readonly_fields = (
        "asset_id", "assigned_at", "created_at", "qc_checked_at",
        "release_ready_flag", "bom_verified_flag", "reservation_active_flag",
    )
    inlines = [ROAssetComponentInline]
    ordering = ("-id",)

    @admin.display(boolean=True, description="BOM verified")
    def bom_verified_flag(self, obj):
        return obj.bom_verified

    @admin.display(boolean=True, description="Release ready")
    def release_ready_flag(self, obj):
        return obj.release_ready

    @admin.display(boolean=True, description="Reserved")
    def reservation_active_flag(self, obj):
        return obj.reservation_active


@admin.register(ROAssetComponent)
class ROAssetComponentAdmin(admin.ModelAdmin):
    list_display = (
        "asset", "part", "quantity", "serial_number", "source", "status",
        "scan_status", "installed_at", "warranty_end", "replacement_due",
    )
    list_filter = ("status", "scan_status", "source", "part__category")
    search_fields = (
        "asset__asset_id", "asset__serial_number", "part__code", "part__name",
        "serial_number", "batch_number", "source_reference",
    )
    autocomplete_fields = ("asset", "part", "inventory_item", "installed_by")

    @admin.display(description="Warranty ends")
    def warranty_end(self, obj):
        return obj.warranty_end_date or "—"

    @admin.display(description="Replacement due")
    def replacement_due(self, obj):
        return obj.replacement_due_date or "—"


@admin.register(ROAssetComponentEvent)
class ROAssetComponentEventAdmin(admin.ModelAdmin):
    list_display = ("asset", "part", "action", "serial_number", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = (
        "asset__asset_id", "asset__serial_number", "part__code", "part__name",
        "serial_number", "source_reference", "remarks",
    )
    readonly_fields = [field.name for field in ROAssetComponentEvent._meta.fields]
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ROAssetMovement)
class ROAssetMovementAdmin(admin.ModelAdmin):
    list_display = (
        "asset", "action", "customer", "from_status", "to_status",
        "request_number", "performed_by", "created_at",
    )
    list_filter = ("action", "from_status", "to_status", "created_at")
    search_fields = (
        "asset__asset_id", "asset__serial_number", "customer__name",
        "request_number", "remarks",
    )
    readonly_fields = [field.name for field in ROAssetMovement._meta.fields]
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ROStockAuditItemInline(admin.TabularInline):
    model = ROStockAuditItem
    extra = 0
    fields = (
        "asset", "expected_status", "physically_found", "scanned_at",
        "scanned_by", "remarks",
    )
    readonly_fields = fields
    can_delete = False


@admin.register(ROStockAudit)
class ROStockAuditAdmin(admin.ModelAdmin):
    list_display = ("reference", "status", "started_by", "started_at", "completed_at")
    list_filter = ("status", "started_at")
    search_fields = ("reference", "notes")
    readonly_fields = ("reference", "started_by", "started_at", "completed_at")
    inlines = [ROStockAuditItemInline]


@admin.register(ROStockAuditItem)
class ROStockAuditItemAdmin(admin.ModelAdmin):
    list_display = (
        "audit", "asset", "expected_status", "physically_found", "scanned_at", "scanned_by",
    )
    list_filter = ("physically_found", "expected_status")
    search_fields = ("audit__reference", "asset__asset_id", "asset__serial_number")
    readonly_fields = [field.name for field in ROStockAuditItem._meta.fields]
