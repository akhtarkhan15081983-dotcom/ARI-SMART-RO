from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User

from .models import Company, CompanyMembership, CompanySubscription, SubscriptionPlan


class SaaSFoundationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            phone="9000011111", password="StrongPass123!", role="ADMIN", is_verified=True,
        )

    def test_public_can_view_commercial_plans(self):
        response = self.client.get("/api/saas/plans/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["plans"]), 3)

    def test_public_brand_endpoint_exposes_only_safe_white_label_config(self):
        response = self.client.get("/api/saas/brand/ari-smart-ro/")
        self.assertEqual(response.status_code, 200)
        brand = response.data["brand"]
        self.assertEqual(brand["slug"], "ari-smart-ro")
        self.assertNotIn("gstin", brand)
        self.assertNotIn("subscription", brand)

    def test_authorised_owner_can_create_isolated_company_with_trial(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/saas/companies/create/",
            {"name": "Pure Water Co", "slug": "pure-water-co", "phone": "9000011111", "city": "Delhi"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        company = Company.objects.get(slug="pure-water-co")
        membership = CompanyMembership.objects.get(company=company, user=self.owner)
        self.assertEqual(membership.role, "OWNER")
        self.assertEqual(company.subscription.status, "TRIAL")
        self.assertTrue(company.subscription.has_access)

    def test_customer_cannot_create_business_tenant(self):
        customer = User.objects.create_user(
            phone="9000011112", password="StrongPass123!", role="CUSTOMER", is_verified=True,
        )
        self.client.force_authenticate(customer)
        response = self.client.post(
            "/api/saas/companies/create/",
            {"name": "Unsafe Co", "slug": "unsafe-co", "phone": "9000011112"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Company.objects.filter(slug="unsafe-co").exists())

    def test_my_companies_never_returns_another_company(self):
        plan = SubscriptionPlan.objects.get(code="starter")
        mine = Company.objects.create(name="Mine", slug="mine", phone="9000011111")
        other = Company.objects.create(name="Other", slug="other", phone="9000011113")
        CompanyMembership.objects.create(company=mine, user=self.owner, role="OWNER")
        CompanySubscription.objects.create(
            company=mine, plan=plan, status="ACTIVE", current_period_end=timezone.now() + timedelta(days=30),
        )
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/saas/companies/")
        self.assertEqual(response.status_code, 200)
        slugs = [row["company"]["slug"] for row in response.data["memberships"]]
        self.assertIn("mine", slugs)
        self.assertNotIn(other.slug, slugs)

    def test_normal_company_admin_cannot_open_platform_dashboard(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/saas/super-admin/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_view_metrics_and_change_subscription_status(self):
        superuser = User.objects.create_superuser(phone="9000011199", password="StrongPass123!")
        company = Company.objects.get(slug="ari-smart-ro")
        self.client.force_authenticate(superuser)
        response = self.client.get("/api/saas/super-admin/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("monthly_recurring_revenue", response.data["metrics"])
        update = self.client.post(
            f"/api/saas/super-admin/companies/{company.id}/subscription-status/",
            {"status": "PAUSED"},
            format="json",
        )
        self.assertEqual(update.status_code, 200)
        company.subscription.refresh_from_db()
        self.assertEqual(company.subscription.status, "PAUSED")

    def test_superuser_can_onboard_complete_company(self):
        superuser = User.objects.create_superuser(phone="9000011198", password="StrongPass123!")
        self.client.force_authenticate(superuser)
        response = self.client.post(
            "/api/saas/super-admin/companies/onboard/",
            {
                "name": "National Pure Water",
                "legal_name": "National Pure Water Private Limited",
                "slug": "national-pure-water",
                "phone": "9000011100",
                "email": "office@example.com",
                "city": "Delhi",
                "state": "Delhi",
                "owner_name": "Ravi Owner",
                "owner_phone": "9000011101",
                "initial_password": "OwnerStrong@123",
                "plan_code": "growth",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        company = Company.objects.get(slug="national-pure-water")
        self.assertEqual(company.branches.filter(is_head_office=True).count(), 1)
        self.assertEqual(company.subscription.plan.code, "growth")
        self.assertEqual(company.subscription.status, "TRIAL")
        owner = User.objects.get(phone="9000011101")
        self.assertFalse(owner.is_superuser)
        self.assertEqual(CompanyMembership.objects.get(company=company, user=owner).role, "OWNER")

    def test_company_lifecycle_requires_reason_and_keeps_audit_history(self):
        superuser = User.objects.create_superuser(phone="9000011197", password="StrongPass123!")
        company = Company.objects.get(slug="ari-smart-ro")
        self.client.force_authenticate(superuser)
        invalid = self.client.post(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle/",
            {"action": "SUSPEND", "reason": "x"}, format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        response = self.client.post(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle/",
            {"action": "SUSPEND", "reason": "Security review requested"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        company.refresh_from_db()
        self.assertEqual(company.lifecycle_status, "SUSPENDED")
        self.assertFalse(company.is_active)
        history = self.client.get(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle-history/"
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["events"][0]["action"], "SUSPEND")

    def test_deletion_has_archive_and_30_day_grace_guards(self):
        superuser = User.objects.create_superuser(phone="9000011196", password="StrongPass123!")
        company = Company.objects.get(slug="ari-smart-ro")
        self.client.force_authenticate(superuser)
        premature = self.client.post(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle/",
            {"action": "REQUEST_DELETION", "reason": "Business closure confirmed"}, format="json",
        )
        self.assertEqual(premature.status_code, 409)
        self.client.post(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle/",
            {"action": "ARCHIVE", "reason": "Business closure confirmed"}, format="json",
        )
        requested = self.client.post(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle/",
            {"action": "REQUEST_DELETION", "reason": "Business closure confirmed"}, format="json",
        )
        self.assertEqual(requested.status_code, 200)
        company.refresh_from_db()
        self.assertEqual(company.lifecycle_status, "PENDING_DELETION")
        blocked = self.client.delete(
            f"/api/saas/super-admin/companies/{company.id}/lifecycle/",
            {"confirmation": company.slug, "reason": "Permanent closure requested"}, format="json",
        )
        self.assertEqual(blocked.status_code, 409)

    def test_superuser_can_edit_company_profile_with_audit_event(self):
        superuser = User.objects.create_superuser(phone="9000011195", password="StrongPass123!")
        company = Company.objects.get(slug="ari-smart-ro")
        self.client.force_authenticate(superuser)
        response = self.client.patch(
            f"/api/saas/super-admin/companies/{company.id}/",
            {"app_display_name": "ARI Business Suite", "support_phone": "9876543210"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        company.refresh_from_db()
        self.assertEqual(company.app_display_name, "ARI Business Suite")
        self.assertEqual(company.lifecycle_events.first().action, "UPDATE_PROFILE")

    def test_non_ari_tenant_admin_cannot_read_shared_operational_data(self):
        plan = SubscriptionPlan.objects.get(code="starter")
        company = Company.objects.create(name="Bhawna RO", slug="bhawna-ro", phone="9000011188")
        CompanyMembership.objects.create(company=company, user=self.owner, role="OWNER")
        CompanySubscription.objects.create(
            company=company, plan=plan, status="ACTIVE",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        token = str(RefreshToken.for_user(self.owner).access_token)
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/customers/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["detail"].code,
            "tenant_operational_data_not_provisioned",
        )
        safe = self.client.get("/api/saas/companies/")
        self.assertEqual(safe.status_code, 200)
