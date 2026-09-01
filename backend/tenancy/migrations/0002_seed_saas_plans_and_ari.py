from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def seed_saas(apps, schema_editor):
    Plan = apps.get_model("tenancy", "SubscriptionPlan")
    Company = apps.get_model("tenancy", "Company")
    Branch = apps.get_model("tenancy", "Branch")
    Membership = apps.get_model("tenancy", "CompanyMembership")
    Subscription = apps.get_model("tenancy", "CompanySubscription")
    User = apps.get_model("accounts", "User")

    plans = [
        ("starter", "Starter", "1499.00", 5, 250, 1, ["Customer CRM", "Service & complaints", "Basic reports"]),
        ("growth", "Growth", "3999.00", 20, 2000, 3, ["Rental management", "Inventory", "HRMS", "Advanced reports"]),
        ("professional", "Professional", "9999.00", 75, 10000, 10, ["All operations", "Multi-branch", "Automation", "Priority support"]),
        ("enterprise", "Enterprise", "0.00", 100000, 1000000, 1000, ["White label", "Custom limits", "Dedicated onboarding", "Enterprise support"]),
    ]
    saved = {}
    for order, (code, name, price, employees, customers, branches, features) in enumerate(plans, start=1):
        saved[code], _ = Plan.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": f"ARI SMART RO {name} business platform",
                "price": price,
                "billing_interval": "MONTHLY",
                "employee_limit": employees,
                "customer_limit": customers,
                "branch_limit": branches,
                "features": features,
                "is_public": code != "enterprise",
                "is_active": True,
                "sort_order": order,
            },
        )

    company, _ = Company.objects.get_or_create(
        slug="ari-smart-ro",
        defaults={
            "name": "ARI SMART RO",
            "legal_name": "ARI SMART RO",
            "phone": "8923908729",
            "support_phone": "8923908729",
            "timezone": "Asia/Kolkata",
            "is_active": True,
        },
    )
    branch, _ = Branch.objects.get_or_create(
        company=company,
        code="HO",
        defaults={"name": "Head Office", "phone": company.phone, "is_head_office": True, "is_active": True},
    )
    role_map = {"ADMIN": "OWNER", "MANAGER": "MANAGER", "OFFICE": "STAFF", "ENGINEER": "STAFF"}
    for user in User.objects.filter(role__in=role_map):
        Membership.objects.get_or_create(
            company=company,
            user=user,
            defaults={"role": role_map[user.role], "branch": branch, "is_active": True},
        )
    now = timezone.now()
    Subscription.objects.get_or_create(
        company=company,
        defaults={
            "plan": saved["enterprise"],
            "status": "ACTIVE",
            "starts_at": now,
            "current_period_end": now + timedelta(days=3650),
        },
    )


def reverse_seed(apps, schema_editor):
    apps.get_model("tenancy", "Company").objects.filter(slug="ari-smart-ro").delete()
    apps.get_model("tenancy", "SubscriptionPlan").objects.filter(
        code__in=["starter", "growth", "professional", "enterprise"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("tenancy", "0001_initial"), ("accounts", "0006_customer_engagement")]
    operations = [migrations.RunPython(seed_saas, reverse_seed)]
