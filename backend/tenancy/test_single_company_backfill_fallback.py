from django.test import SimpleTestCase

from tenancy.inventory_tenant_backfill import decide
from tenancy.tenant_backfill import _decision


class SingleCompanyBackfillFallbackTests(SimpleTestCase):
    def test_operational_fallback_resolves_only_when_no_evidence_exists(self):
        decision = _decision(
            "Customer",
            101,
            None,
            [],
            fallback_company_id=7,
        )
        self.assertEqual(decision.status, "RESOLVED")
        self.assertEqual(decision.company_id, 7)
        self.assertEqual(decision.evidence, (("single_company_database", 7),))

    def test_operational_fallback_does_not_override_conflicting_evidence(self):
        decision = _decision(
            "Customer",
            102,
            None,
            [("assigned_engineer", 7), ("job_engineer", 8)],
            fallback_company_id=7,
        )
        self.assertEqual(decision.status, "CONFLICT")
        self.assertIsNone(decision.company_id)

    def test_inventory_fallback_resolves_only_when_no_evidence_exists(self):
        decision = decide(
            "Supplier",
            201,
            None,
            [],
            fallback_company_id=7,
        )
        self.assertEqual(decision.status, "RESOLVED")
        self.assertEqual(decision.company_id, 7)
        self.assertEqual(decision.evidence, (("single_company_database", 7),))

    def test_inventory_fallback_does_not_override_conflicting_evidence(self):
        decision = decide(
            "Purchase",
            202,
            None,
            [("supplier_evidence", 7), ("bag_engineer", 8)],
            fallback_company_id=7,
        )
        self.assertEqual(decision.status, "CONFLICT")
        self.assertIsNone(decision.company_id)
