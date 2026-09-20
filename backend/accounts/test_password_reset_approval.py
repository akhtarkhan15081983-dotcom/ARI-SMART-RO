from django.test import TestCase

from rest_framework.test import APIClient

from tenancy.models import Company, CompanyMembership

from .models import PasswordResetRequest, User


class AdminApprovedPasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(
            name="ARI SMART RO",
            slug="ari-smart-ro-password-reset-test",
            phone="9000000000",
            is_active=True,
            lifecycle_status="ACTIVE",
        )
        self.admin = User.objects.create_user(
            phone="9000000001",
            password="AdminStrong@123",
            first_name="Admin",
            role="ADMIN",
            is_verified=True,
            is_active=True,
        )
        self.employee = User.objects.create_user(
            phone="9000000002",
            password="OldStrong@123",
            first_name="Engineer",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.admin,
            role="OWNER",
            is_active=True,
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.employee,
            role="STAFF",
            is_active=True,
        )

    def test_employee_can_request_admin_approved_reset_and_use_one_time_code(self):
        response = self.client.post(
            "/api/auth/forgot-password/request/",
            {"phone": self.employee.phone},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        reset_request = PasswordResetRequest.objects.get(user=self.employee)
        self.assertEqual(reset_request.status, "PENDING")

        self.client.force_authenticate(user=self.admin)
        list_response = self.client.get("/api/auth/admin/password-reset-requests/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data["requests"]), 1)

        approval = self.client.post(
            f"/api/auth/admin/password-reset-requests/{reset_request.id}/review/",
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(approval.status_code, 200)
        code = approval.data["reset_code"]
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

        self.client.force_authenticate(user=None)
        completion = self.client.post(
            "/api/auth/forgot-password/complete/",
            {
                "phone": self.employee.phone,
                "code": code,
                "new_password": "NewStrong@456",
            },
            format="json",
        )
        self.assertEqual(completion.status_code, 200)

        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password("NewStrong@456"))
        reset_request.refresh_from_db()
        self.assertEqual(reset_request.status, "USED")
        self.assertEqual(reset_request.code_hash, "")

    def test_unknown_phone_does_not_reveal_account_existence(self):
        response = self.client.post(
            "/api/auth/forgot-password/request/",
            {"phone": "9999999999"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(PasswordResetRequest.objects.count(), 0)

    def test_admin_cannot_approve_own_reset(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/auth/forgot-password/request/",
            {"phone": self.admin.phone},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        reset_request = PasswordResetRequest.objects.get(user=self.admin)
        self.client.force_authenticate(user=self.admin)
        approval = self.client.post(
            f"/api/auth/admin/password-reset-requests/{reset_request.id}/review/",
            {"action": "approve"},
            format="json",
        )
        self.assertEqual(approval.status_code, 400)
