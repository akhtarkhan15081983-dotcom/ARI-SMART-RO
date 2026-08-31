from django.contrib import admin
from .models import Customer, CustomerLocationLog


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):

    list_display = (
        "customer_id",
        "name",
        "phone",
        "area",
        "ro_model",
        "assigned_engineer",
        "monthly_rent",
        "is_active",
    )

    search_fields = (
        "customer_id",
        "name",
        "phone",
        "area",
    )

    list_filter = (
        "assigned_engineer",
        "city",
        "is_active",
    )

    readonly_fields = (
        "customer_id",
        "created_at",
    )

    autocomplete_fields = (
        "assigned_engineer",
    )


@admin.register(CustomerLocationLog)
class CustomerLocationLogAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "captured_by",
        "latitude",
        "longitude",
        "accuracy",
        "source",
        "captured_at",
    )
    search_fields = (
        "customer__customer_id",
        "customer__name",
        "customer__phone",
        "captured_by__employee_id",
    )
    list_filter = ("source", "captured_at")
    readonly_fields = (
        "customer",
        "captured_by",
        "latitude",
        "longitude",
        "accuracy",
        "source",
        "captured_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
