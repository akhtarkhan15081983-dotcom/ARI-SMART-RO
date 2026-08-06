from django.contrib import admin
from .models import Supplier
from .models import Purchase, PurchaseItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "is_active")
    search_fields = ("name", "phone")
    list_filter = ("is_active",)




class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "supplier",
        "invoice_date",
    )

    list_filter = (
        "supplier",
        "invoice_date",
    )

    search_fields = (
        "invoice_number",
    )

    inlines = [PurchaseItemInline]