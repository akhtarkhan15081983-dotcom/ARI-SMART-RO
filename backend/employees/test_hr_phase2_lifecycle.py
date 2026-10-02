from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from tenancy.models import Company, CompanyMembership
from .models import EmployeeProfile
from .hr_lifecycle_models import EmployeeHrLifecycle
from .hr_phase2_lifecycle_models import EmployeeLifecycleAction, EmployeeLifecycleAudit, ExitCase


class CorporateHrPhase2LifecycleTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.company = Company.objects.create(name="Lifecycle Tenant", slug="lifecycle-tenant", phone="9222200000", is_active=True, lifecycle_status="ACTIVE")
        self.other = Company.objects.create(name="Foreign Lifecycle", slug="foreign-lifecycle", phone="9222290000", is_active=True, lifecycle_status="ACTIVE")
        self.admin = User.objects.create_user(phone="9222200001", password="Strong@Test1", role="ADMIN", first_name="Admin", is_verified=True)
        self.office = User.objects.create_user(phone="9222200002", password="Strong@Test1", role="OFFICE", first_name="HR", is_verified=True)
        self.manager_user = User.objects.create_user(phone="9222200003", password="Strong@Test1", role="MANAGER", first_name="Manager", is_verified=True)
        self.employee_user = User.objects.create_user(phone="9222200004", password="Strong@Test1", role="ENGINEER", first_name="Employee", is_verified=True)
        self.foreign_admin = User.objects.create_user(phone="9222290001", password="Strong@Test1", role="ADMIN", first_name="Foreign", is_verified=True)
        for user, role in [(self.admin, "OWNER"), (self.office, "STAFF"), (self.manager_user, "STAFF"), (self.employee_user, "STAFF")]:
            CompanyMembership.objects.create(company=self.company, user=user, role=role, is_active=True)
        CompanyMembership.objects.create(company=self.other, user=self.foreign_admin, role="OWNER", is_active=True)
        self.manager = EmployeeProfile.objects.create(company=self.company, user=self.manager_user, employee_id="MGR-1", joining_date=self.today, designation="MANAGER", job_title="Service Manager", department="Service", salary=Decimal("45000"), gender="OTHER")
        self.employee = EmployeeProfile.objects.create(company=self.company, user=self.employee_user, employee_id="EMP-LIFE-1", joining_date=self.today, designation="ENGINEER", job_title="Service Engineer", department="Service", salary=Decimal("28000"), gender="OTHER", reporting_manager=self.manager)
        self.foreign_manager = EmployeeProfile.objects.create(company=self.other, user=self.foreign_admin, employee_id="FOREIGN-1", joining_date=self.today, designation="MANAGER", salary=Decimal("50000"), gender="OTHER")
        life = self.employee.hr_lifecycle
        life.employment_type = "PROBATION"; life.employment_status = "PROBATION"; life.confirmation_due_date = self.today + timedelta(days=10); life.save()
        self.actions = "/api/employees/hrms/lifecycle/actions/"
        self.exits = "/api/employees/hrms/lifecycle/exits/"

    def _auth(self, user): self.client.force_authenticate(user)

    def _create_action(self, action_type, proposed=None, reason="Approved business requirement"):
        self._auth(self.office)
        return self.client.post(self.actions, {"employee_id": self.employee.id, "action_type": action_type, "effective_date": str(self.today), "reason": reason, "proposed_changes": proposed or {}}, format="json")

    def test_cross_company_employee_is_rejected(self):
        self._auth(self.foreign_admin)
        response = self.client.post(self.actions, {"employee_id": self.employee.id, "action_type": "CONFIRMATION", "effective_date": str(self.today)}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_probation_extension_requires_reason(self):
        response = self._create_action("PROBATION_EXTENSION", {"extension_months": 3}, reason="")
        self.assertEqual(response.status_code, 400)

    def test_cross_company_reporting_manager_is_rejected(self):
        response = self._create_action("TRANSFER", {"reporting_manager_id": self.foreign_manager.id, "department": "Operations"})
        self.assertEqual(response.status_code, 400)

    def test_snapshot_and_audit_are_created(self):
        response = self._create_action("INCREMENT", {"salary": "32000"})
        self.assertEqual(response.status_code, 201)
        row = EmployeeLifecycleAction.objects.get(id=response.data["id"])
        self.assertEqual(row.snapshot_before["salary"], "28000.00")
        self.assertTrue(EmployeeLifecycleAudit.objects.filter(entity_type="LIFECYCLE_ACTION", entity_id=row.id, action="CREATE").exists())

    def test_self_manager_review_is_forbidden(self):
        self._auth(self.admin)
        row = EmployeeLifecycleAction.objects.create(company=self.company, employee=self.employee, action_type="CONFIRMATION", effective_date=self.today, status="MANAGER_REVIEW", reason="review", created_by=self.admin)
        self._auth(self.employee_user)
        response = self.client.post(f"{self.actions}{row.id}/workflow/", {"action": "MANAGER_REVIEW", "assessment": {"note": "self"}}, format="json")
        self.assertIn(response.status_code, {403, 400})

    def test_exit_creates_four_default_clearances_and_is_tenant_scoped(self):
        self._auth(self.office)
        response = self.client.post(self.exits, {"employee_id": self.employee.id, "separation_type": "RESIGNATION", "resignation_date": str(self.today), "notice_days": 30, "proposed_last_working_date": str(self.today + timedelta(days=30)), "reason": "Personal resignation"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data["clearances"]), 4)
        self._auth(self.foreign_admin)
        foreign = self.client.get(self.exits)
        self.assertEqual(foreign.status_code, 200)
        self.assertEqual(foreign.data, [])

    def test_exit_waiver_requires_reason_and_settlement_gate_blocks_approval(self):
        self._auth(self.office)
        created = self.client.post(self.exits, {"employee_id": self.employee.id, "separation_type": "RESIGNATION", "resignation_date": str(self.today), "notice_days": 30, "proposed_last_working_date": str(self.today + timedelta(days=30)), "reason": "Resignation"}, format="json")
        case_id = created.data["id"]
        self.client.post(f"{self.exits}{case_id}/action/", {"action": "START_CLEARANCE"}, format="json")
        clearance_id = created.data["clearances"][0]["id"]
        waived = self.client.post(f"{self.exits}{case_id}/clearances/{clearance_id}/action/", {"status": "WAIVED"}, format="json")
        self.assertEqual(waived.status_code, 400)
        submitted = self.client.post(f"{self.exits}{case_id}/action/", {"action": "SUBMIT_APPROVAL"}, format="json")
        self.assertEqual(submitted.status_code, 400)

    def test_post_separation_letter_is_blocked_before_separation(self):
        self._auth(self.office)
        created = self.client.post(self.exits, {"employee_id": self.employee.id, "separation_type": "TERMINATION", "notice_days": 0, "proposed_last_working_date": str(self.today), "reason": "Policy decision"}, format="json")
        response = self.client.post(f"{self.exits}{created.data['id']}/post-separation-letter/", {"letter_type": "EXPERIENCE"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_timeline_and_command_center_are_tenant_scoped(self):
        self._auth(self.admin)
        timeline = self.client.get(f"/api/employees/hrms/lifecycle/employees/{self.employee.id}/timeline/")
        dashboard = self.client.get("/api/employees/hrms/lifecycle/command-center/")
        self.assertEqual(timeline.status_code, 200)
        self.assertEqual(timeline.data["employee_id"], self.employee.id)
        self.assertEqual(dashboard.status_code, 200)
        self._auth(self.foreign_admin)
        foreign = self.client.get(f"/api/employees/hrms/lifecycle/employees/{self.employee.id}/timeline/")
        self.assertEqual(foreign.status_code, 404)
