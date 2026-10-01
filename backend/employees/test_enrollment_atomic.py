from unittest.mock import patch

from django.test import TransactionTestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from employees.enrollment_atomic import TransactionSafeFaceEnrollmentAPIView
from employees.models import EmployeeProfile


class TransactionSafeFaceEnrollmentTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            phone="9000000001",
            password="TestOnlyPassword!123",
            first_name="Atomic",
            role="ENGINEER",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            gender="MALE",
            joining_date="2026-09-30",
            designation="ENGINEER",
            face_enrollment_allowed=True,
        )

    def _request(self):
        request = self.factory.post("/api/employees/face-enrollment/", {})
        force_authenticate(request, user=self.user)
        return request

    def test_database_changes_roll_back_if_enrollment_fails_mid_request(self):
        def fail_after_mutation(view, request):
            employee = EmployeeProfile.objects.get(user=request.user)
            employee.attendance_device_id = "temporary-device"
            employee.face_enrollment_allowed = False
            employee.save(
                update_fields=["attendance_device_id", "face_enrollment_allowed"]
            )
            raise RuntimeError("simulated post-save failure")

        with patch(
            "employees.enrollment_atomic.SecureFaceEnrollmentAPIView.post",
            autospec=True,
            side_effect=fail_after_mutation,
        ):
            with self.assertRaises(RuntimeError):
                TransactionSafeFaceEnrollmentAPIView.as_view()(self._request())

        self.employee.refresh_from_db()
        self.assertEqual(self.employee.attendance_device_id, "")
        self.assertTrue(self.employee.face_enrollment_allowed)

    def test_database_changes_commit_when_enrollment_succeeds(self):
        def succeed_after_mutation(view, request):
            employee = EmployeeProfile.objects.get(user=request.user)
            employee.attendance_device_id = "approved-device"
            employee.face_enrollment_allowed = False
            employee.save(
                update_fields=["attendance_device_id", "face_enrollment_allowed"]
            )
            return Response({"success": True}, status=200)

        with patch(
            "employees.enrollment_atomic.SecureFaceEnrollmentAPIView.post",
            autospec=True,
            side_effect=succeed_after_mutation,
        ):
            response = TransactionSafeFaceEnrollmentAPIView.as_view()(self._request())

        self.assertEqual(response.status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.attendance_device_id, "approved-device")
        self.assertFalse(self.employee.face_enrollment_allowed)

    def test_missing_employee_profile_is_rejected_without_calling_base_view(self):
        other_user = User.objects.create_user(
            phone="9000000002",
            password="TestOnlyPassword!123",
            first_name="NoProfile",
            role="ENGINEER",
            is_verified=True,
        )
        request = self.factory.post("/api/employees/face-enrollment/", {})
        force_authenticate(request, user=other_user)

        with patch(
            "employees.enrollment_atomic.SecureFaceEnrollmentAPIView.post",
            autospec=True,
        ) as base_post:
            response = TransactionSafeFaceEnrollmentAPIView.as_view()(request)

        self.assertEqual(response.status_code, 404)
        base_post.assert_not_called()
