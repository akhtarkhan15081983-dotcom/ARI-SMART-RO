from datetime import date

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from complaints.models import Complaint
from customers.models import Customer
from employees.models import EmployeeProfile
from jobs.models import Job
from service.views import _linked_customer_for
from tenancy.models import Company, CompanyMembership


class OperationalTenantSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company_a = Company.objects.create(
            name="Tenant A",
            slug="max-pro-tenant-a",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.company_b = Company.objects.create(
            name="Tenant B",
            slug="max-pro-tenant-b",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9600000001",
            password="StrongAdmin@123",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company_a,
            user=self.admin,
            role="ADMIN",
            is_active=True,
        )

        self.engineer_a_user = User.objects.create_user(
            phone="9600000002",
            password="StrongStaff@123",
            first_name="Engineer A",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer_b_user = User.objects.create_user(
            phone="9600000003",
            password="StrongStaff@123",
            first_name="Engineer B",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        self.engineer_a = EmployeeProfile.objects.create(
            company=self.company_a,
            user=self.engineer_a_user,
            employee_id="EMP-TENANT-A",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.engineer_b = EmployeeProfile.objects.create(
            company=self.company_b,
            user=self.engineer_b_user,
            employee_id="EMP-TENANT-B",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )

        self.customer = Customer.objects.create(
            name="Tenant Customer",
            phone="9700000001",
            address="Test Address",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TEST",
            assigned_engineer=self.engineer_a,
        )
        self.complaint = Complaint.objects.create(
            customer=self.customer,
            engineer=self.engineer_a,
            complaint_type="OTHER",
            description="Test complaint",
        )
        self.job_b = Job.objects.create(
            customer=self.customer,
            engineer=self.engineer_b,
            job_type="SERVICE",
            scheduled_date=timezone.now(),
            customer_otp="123456",
            otp_created_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.admin)

    def test_customer_assignment_rejects_other_tenant_employee(self):
        response = self.client.post(
            f"/api/customers/{self.customer.id}/assign/",
            {"employee_id": self.engineer_b.id},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.assigned_engineer_id, self.engineer_a.id)

    def test_complaint_assignment_rejects_other_tenant_engineer(self):
        response = self.client.patch(
            f"/api/complaints/{self.complaint.id}/assign/",
            {"engineer": self.engineer_b.id},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.engineer_id, self.engineer_a.id)

    def test_complaint_generic_update_cannot_bypass_assignment_guard(self):
        response = self.client.patch(
            f"/api/complaints/{self.complaint.id}/update/",
            {"engineer": self.engineer_b.id, "status": "CLOSED"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.engineer_id, self.engineer_a.id)
        self.assertNotEqual(self.complaint.status, "CLOSED")

    def test_admin_job_otp_rejects_job_owned_by_other_tenant_engineer(self):
        response = self.client.get(f"/api/jobs/{self.job_b.id}/admin-otp/")
        self.assertEqual(response.status_code, 404)


class SharedPhoneCustomerScopeTests(TestCase):
    def _legacy_pair(self, phone):
        first = Customer.objects.create(
            name="Shared Phone One",
            phone=phone,
            address="Address 1",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI ONE",
        )
        second = Customer.objects.create(
            name="Shared Phone Two",
            phone=phone,
            address="Address 2",
            city="Agra",
            state="Uttar Pradesh",
            pincode="282001",
            ro_model="ARI TWO",
        )
        return first, second

    def test_service_customer_resolution_claims_one_deterministic_legacy_record(self):
        user = User.objects.create_user(
            phone="9800000001",
            password="CustomerStrong@123",
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )
        first, second = self._legacy_pair(user.phone)

        resolved = _linked_customer_for(user)

        self.assertEqual(resolved.id, first.id)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.user_id, user.id)
        self.assertIsNone(second.user_id)
        self.assertEqual(_linked_customer_for(user).id, first.id)

    def test_complaint_list_does_not_expose_second_shared_phone_customer(self):
        user = User.objects.create_user(
            phone="9800000002",
            password="CustomerStrong@123",
            role="CUSTOMER",
            is_verified=True,
            is_active=True,
        )
        first, second = self._legacy_pair(user.phone)
        visible = Complaint.objects.create(
            customer=first,
            complaint_type="OTHER",
            description="Visible complaint",
        )
        hidden = Complaint.objects.create(
            customer=second,
            complaint_type="OTHER",
            description="Hidden complaint",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/complaints/")

        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.data}
        self.assertIn(visible.id, ids)
        self.assertNotIn(hidden.id, ids)
