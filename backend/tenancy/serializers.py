from rest_framework import serializers

from .models import Company, CompanyLifecycleEvent, CompanyMembership, CompanySubscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "code", "name", "description", "price", "billing_interval",
            "employee_limit", "customer_limit", "branch_limit", "features",
        ]


class CompanySubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    has_access = serializers.BooleanField(read_only=True)

    class Meta:
        model = CompanySubscription
        fields = ["status", "starts_at", "current_period_end", "trial_ends_at", "cancel_at_period_end", "has_access", "plan"]


class CompanySerializer(serializers.ModelSerializer):
    subscription = CompanySubscriptionSerializer(read_only=True)

    class Meta:
        model = Company
        fields = [
            "id", "name", "legal_name", "slug", "phone", "email", "gstin",
            "logo", "primary_color", "secondary_color", "support_phone",
            "support_email", "app_display_name", "tagline", "welcome_message",
            "show_public_shop", "enabled_modules", "address", "city", "state", "pincode", "timezone",
            "is_active", "lifecycle_status", "lifecycle_reason", "archived_at",
            "deletion_scheduled_for", "subscription",
        ]
        read_only_fields = [
            "id", "is_active", "lifecycle_status", "lifecycle_reason", "archived_at",
            "deletion_scheduled_for", "subscription",
        ]


class CompanyLifecycleEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = CompanyLifecycleEvent
        fields = [
            "id", "action", "previous_status", "new_status", "reason",
            "actor_name", "metadata", "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System"
        return obj.actor.get_full_name() or obj.actor.phone


class PublicCompanyBrandSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "slug", "display_name", "tagline", "welcome_message", "logo_url",
            "primary_color", "secondary_color", "support_phone", "support_email",
            "show_public_shop", "enabled_modules", "city", "state",
        ]

    def get_logo_url(self, obj):
        if not obj.logo:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url


class MembershipSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = CompanyMembership
        fields = ["id", "role", "branch", "is_active", "joined_at", "company"]
        read_only_fields = ["id", "branch", "is_active", "joined_at", "company"]
