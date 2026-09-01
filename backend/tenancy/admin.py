from django.contrib import admin

from .models import Branch, Company, CompanyLifecycleEvent, CompanyMembership, CompanySubscription, SubscriptionPlan


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "city", "lifecycle_status", "is_active", "created_at")
    list_filter = ("lifecycle_status", "is_active", "state")
    search_fields = ("name", "legal_name", "phone", "gstin")
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(Branch)
admin.site.register(CompanyMembership)
admin.site.register(CompanySubscription)
admin.site.register(SubscriptionPlan)


@admin.register(CompanyLifecycleEvent)
class CompanyLifecycleEventAdmin(admin.ModelAdmin):
    list_display = ("company_slug", "action", "previous_status", "new_status", "actor", "created_at")
    list_filter = ("action", "new_status", "created_at")
    search_fields = ("company_name", "company_slug", "reason")
    readonly_fields = (
        "company", "company_name", "company_slug", "action", "previous_status",
        "new_status", "reason", "actor", "metadata", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
