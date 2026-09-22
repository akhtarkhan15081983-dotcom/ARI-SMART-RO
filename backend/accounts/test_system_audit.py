from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.audit import write_audit_event
from accounts.models import SystemAuditEvent, User
from tenancy.models import Company


class SystemAuditEventTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            phone="9111111111",
            password="StrongPass123!",
            first_name="Audit",
            role="ADMIN",
            is_verified=True,
        )
        self.company = Company.objects.create(
            name="Audit Company",
            slug="audit-company",
            phone="9222222222",
            is_active=True,
            lifecycle_status="ACTIVE",
        )

    def test_writer_captures_actor_context_and_state(self):
        request = self.factory.post(
            "/api/example/",
            {},
            format="json",
            HTTP_X_ARI_DEVICE_ID="audit-device-001",
            REMOTE_ADDR="10.0.0.7",
        )
        force_authenticate(request, user=self.user)
        request.user = self.user

        row = write_audit_event(
            request=request,
            action="TEST_CHANGE",
            entity_type="Example",
            entity_id="42",
            company=self.company,
            reason="Verification test",
            before_state={"value": 1},
            after_state={"value": 2},
            metadata={"source": "unit-test"},
        )

        row.refresh_from_db()
        self.assertEqual(row.actor, self.user)
        self.assertEqual(row.company_id, self.company.id)
        self.assertEqual(row.company_name, self.company.name)
        self.assertEqual(row.device_id, "audit-device-001")
        self.assertEqual(str(row.ip_address), "10.0.0.7")
        self.assertEqual(row.reason, "Verification test")
        self.assertEqual(row.before_state, {"value": 1})
        self.assertEqual(row.after_state, {"value": 2})
        self.assertEqual(row.metadata["source"], "unit-test")

    def test_event_is_append_only_by_usage(self):
        request = self.factory.post("/api/example/", {}, format="json")
        force_authenticate(request, user=self.user)
        request.user = self.user

        first = write_audit_event(
            request=request,
            action="FIRST",
            entity_type="Example",
            entity_id="1",
            company=self.company,
        )
        second = write_audit_event(
            request=request,
            action="SECOND",
            entity_type="Example",
            entity_id="1",
            company=self.company,
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(SystemAuditEvent.objects.count(), 2)
