from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AuthSecurityEvent, CustomerEngagement, CustomerEngagementRead, NotificationCampaign, OfferRedemption, SimVerificationChallenge, SmsGatewayDevice, SmsGatewaySubmission, User, UserNotification


@admin.register(CustomerEngagement)
class CustomerEngagementAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "audience", "target_user", "offer_scope", "discount_type", "discount_value", "auto_apply", "valid_until", "is_active")
    list_filter = ("kind", "audience", "offer_scope", "discount_type", "auto_apply", "is_active", "valid_from", "valid_until")
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


@admin.register(NotificationCampaign)
class NotificationCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "priority", "audience", "target_role", "is_active", "created_by", "created_at")
    list_filter = ("category", "priority", "audience", "target_role", "is_active")
    search_fields = ("title", "message")
    filter_horizontal = ("target_users",)
    readonly_fields = ("created_at",)


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "category", "priority", "is_read", "created_at")
    list_filter = ("category", "priority", "is_read", "created_at")
    search_fields = ("user__phone", "user__first_name", "title", "message", "event_key")
    readonly_fields = ("campaign", "event_key", "user", "title", "message", "category", "priority", "action", "action_label", "metadata", "created_at", "read_at")

    def has_add_permission(self, request):
        return False


@admin.register(OfferRedemption)
class OfferRedemptionAdmin(admin.ModelAdmin):
    list_display = ("engagement", "scope", "customer_phone", "base_amount", "discount_amount", "final_amount", "redeemed_at")
    list_filter = ("scope", "redeemed_at")
    search_fields = ("engagement__title", "engagement__promo_code", "customer_phone", "reference")
    readonly_fields = ("engagement", "user", "customer_phone", "scope", "reference", "base_amount", "discount_amount", "final_amount", "redeemed_at")

    def has_add_permission(self, request):
        return False
