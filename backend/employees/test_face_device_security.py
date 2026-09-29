from datetime import date
from unittest.mock import patch

from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIClient

from accounts.models import SystemAuditEvent, User

from .models import EmployeeProfile
from .views import FaceEnrollmentAPIView


class SecureFaceEnrollmentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone="9000099922",
            password="StrongStaff@123",
            role="ENGINEER",
            is_verified=True,
            is_active=True,
            active_login_device_id="approved-phone",
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP-SEC-001",
            gender="MALE",
            joining_date=date(2026, 1, 1),
            designation="ENGINEER",
        )
        self.client.force_authenticate(user=self.user)

    def test_face_enrollment_rejects_device_other_than_authenticated_login_device(self):
        response = self.client.post(
            "/api/employees/face-enrollment/",
            {"device_id": "spoofed-phone"},
            format="multipart",
            HTTP_X_ARI_DEVICE_ID="spoofed-phone",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "FACE_ENROLLMENT_DEVICE_MISMATCH")
        event = SystemAuditEvent.objects.filter(
            action="FACE_ENROLLMENT_DEVICE_MISMATCH_BLOCKED",
            entity_id=str(self.employee.id),
        ).first()
        self.assertIsNotNone(event)

    def test_face_enrollment_requires_bound_login_device(self):
        self.user.active_login_device_id = ""
        self.user.save(update_fields=["active_login_device_id"])

        response = self.client.post(
            "/api/employees/face-enrollment/",
            {"device_id": "new-phone"},
            format="multipart",
            HTTP_X_ARI_DEVICE_ID="new-phone",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "LOGIN_DEVICE_NOT_BOUND")

    @patch.object(FaceEnrollmentAPIView, "post", return_value=Response({"success": True}, status=201))
    def test_matching_device_reaches_existing_enrollment_flow_and_is_audited(self, base_post):
        response = self.client.post(
            "/api/employees/face-enrollment/",
            {"device_id": "approved-phone"},
            format="multipart",
            HTTP_X_ARI_DEVICE_ID="approved-phone",
        )

        self.assertEqual(response.status_code, 201)
        base_post.assert_called_once()
        event = SystemAuditEvent.objects.filter(
            action="FACE_DEVICE_ENROLLMENT_COMPLETED",
            entity_id=str(self.employee.id),
        ).first()
        self.assertIsNotNone(event)
        self.assertTrue(event.metadata["device_matches_login_binding"])
