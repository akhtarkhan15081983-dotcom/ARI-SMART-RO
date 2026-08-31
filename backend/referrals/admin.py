from django.contrib import admin
from .models import ReferralProfile, Referral, WalletReward, WalletLedgerEntry
from .services import approve_referral_review

admin.site.register(ReferralProfile)
admin.site.register(WalletReward)
admin.site.register(WalletLedgerEntry)


@admin.action(description="Approve selected security-review referrals")
def approve_reviews(modeladmin, request, queryset):
    approved = 0
    for referral in queryset.filter(status="REVIEW"):
        approve_referral_review(referral.id)
        approved += 1
    modeladmin.message_user(request, f"{approved} referral review(s) approved.")


@admin.action(description="Reject selected security-review referrals")
def reject_reviews(modeladmin, request, queryset):
    updated = queryset.filter(status="REVIEW").update(
        status="REJECTED",
        rejection_reason="Rejected after security review.",
    )
    modeladmin.message_user(request, f"{updated} referral review(s) rejected.")


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred_user", "status", "referred_type", "created_at")
    list_filter = ("status", "referred_type", "created_at")
    search_fields = ("referrer__phone", "referred_user__phone", "referral_code")
    readonly_fields = ("claim_fingerprint", "risk_reasons", "qualified_at", "created_at", "updated_at")
    actions = (approve_reviews, reject_reviews)
