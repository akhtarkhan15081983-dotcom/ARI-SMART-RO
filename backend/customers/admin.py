from django.contrib import admin
from .models import Customer


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