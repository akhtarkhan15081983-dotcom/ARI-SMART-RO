from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AuthSecurityEvent, CustomerEngagement, CustomerEngagementRead, SimVerificationChallenge, SmsGatewayDevice, SmsGatewaySubmission, User


@admin.register(CustomerEngagement)
class CustomerEngagementAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "audience", "target_user", "discount_type", "discount_value", "valid_until", "is_active")
    list_filter = ("kind", "audience", "discount_type", "is_active", "valid_from", "valid_until")
    search_fields = ("title", "message", "promo_code", "target_user__phone", "target_user__first_name")
    autocomplete_fields = ("target_user",)
    readonly_fields = ("created_at", "created_by")

    def save_model(self, request, obj, form, change):
        if obj.audience == "ALL":
            obj.target_user = None
        if obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CustomerEngagementRead)
class CustomerEngagementReadAdmin(admin.ModelAdmin):
    list_display = ("engagement", "user", "read_at")
    search_fields = ("engagement__title", "user__phone")
    readonly_fields = ("engagement", "user", "read_at")

    def has_add_permission(self, request):
        return False


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


@admin.register(AuthSecurityEvent)
class AuthSecurityEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "ip_address", "device_id", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__phone", "ip_address", "device_id")
    readonly_fields = ("user", "event_type", "ip_address", "device_id", "details", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SmsGatewayDevice)
class SmsGatewayDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "device_id", "phone_number", "is_active", "last_seen_at")
    readonly_fields = ("secret_hash", "last_seen_at", "created_at")


@admin.register(SimVerificationChallenge)
class SimVerificationChallengeAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "expires_at", "verified_by", "verified_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__phone",)
    readonly_fields = ("user", "token_hash", "poll_secret_hash", "status", "expires_at", "verified_at", "verified_by", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(SmsGatewaySubmission)
class SmsGatewaySubmissionAdmin(admin.ModelAdmin):
    list_display = ("gateway", "sender_phone", "accepted", "result_code", "received_at")
    list_filter = ("accepted", "result_code", "received_at")
    readonly_fields = ("gateway", "nonce", "sender_phone", "message_fingerprint", "accepted", "result_code", "received_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
