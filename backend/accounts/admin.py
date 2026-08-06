from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("phone",)

    list_display = (
        "phone",
        "first_name",
        "role",
        "is_staff",
        "is_active",
    )

    fieldsets = (
        (None, {
            "fields": (
                "phone",
                "password",
            )
        }),
        ("Personal Info", {
            "fields": (
                "first_name",
                "last_name",
                "email",
            )
        }),
        ("Role", {
            "fields": (
                "role",
                "is_verified",
            )
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {
            "fields": (
                "last_login",
                "date_joined",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "phone",
                "password1",
                "password2",
                "role",
            ),
        }),
    )

    search_fields = (
        "phone",
        "first_name",
    )