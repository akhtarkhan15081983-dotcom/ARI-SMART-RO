from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import SystemAuditEvent, User
from tenancy.models import Company, CompanyMembership


class AdminSystemAuditAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="Audit API Company",
            slug="audit-api-company",
            phone="9333333333",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9333333334",
            password="StrongPass123!",
            first_name="Audit",
            last_name="Admin",
            role="ADMIN",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        self.other_company = Company.objects.create(
            name="Other Company",
            slug="other-audit-company",
            phone="9333333335",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        SystemAuditEvent.objects.create(
            actor=self.admin,
            action="ROLE_FEATURE_PERMISSION_CHANGED",
            entity_type="RoleFeaturePermission",
            entity_id="7",
            company_id=self.company.id,
            company_name=self.company.name,
            before_state={"is_allowed": True},
            after_state={"is_allowed": False},
        )
        SystemAuditEvent.objects.create(
            actor=self.admin,
            action="SHOULD_NOT_LEAK",
            entity_type="Other",
            entity_id="9",
            company_id=self.other_company.id,
            company_name=self.other_company.name,
        )

    def test_admin_reads_only_current_company_audit_rows(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/auth/admin/system-audit/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["action"], "ROLE_FEATURE_PERMISSION_CHANGED")
        self.assertEqual(response.data[0]["company_id"], self.company.id)

    def test_admin_can_filter_by_action(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            "/api/auth/admin/system-audit/?action=ROLE_FEATURE_PERMISSION_CHANGED"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_non_admin_is_forbidden(self):
        user = User.objects.create_user(
            phone="9333333336",
            password="StrongPass123!",
            role="ENGINEER",
            is_verified=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=user,
            role="STAFF",
            is_active=True,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/auth/admin/system-audit/")
        self.assertEqual(response.status_code, 403)
