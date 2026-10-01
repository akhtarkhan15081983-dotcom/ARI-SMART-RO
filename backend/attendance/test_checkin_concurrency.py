import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from employees.models import EmployeeProfile

from .models import Attendance
from .security import OFFICE_LATITUDE, OFFICE_LONGITUDE


class CheckInConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="ari-attendance-media-")
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.user = User.objects.create_user(
            phone="9000000991",
            password="Strong@Test1",
            role="ENGINEER",
            first_name="Concurrent",
            is_verified=True,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            employee_id="EMP-CONCURRENT-1",
            joining_date=timezone.localdate(),
            designation="ENGINEER",
            gender="MALE",
            salary=Decimal("24000"),
            face_enrolled_at=timezone.now(),
            face_enrollment_verified=True,
            attendance_device_id="device-concurrency-1",
        )

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)
        close_old_connections()

    def _check_in(self, barrier=None):
        close_old_connections()
        user = User.objects.get(pk=self.user.pk)
        client = APIClient()
        client.force_authenticate(user)
        if barrier is not None:
            barrier.wait(timeout=10)
        response = client.post(
            "/api/attendance/check-in/",
            {
                "latitude": str(OFFICE_LATITUDE),
                "longitude": str(OFFICE_LONGITUDE),
                "device_id": "device-concurrency-1",
                "is_mocked": "false",
                "selfie": SimpleUploadedFile(
                    "attendance-selfie.jpg",
                    b"test-selfie-content",
                    content_type="image/jpeg",
                ),
            },
            format="multipart",
        )
        close_old_connections()
        return response.status_code

    def test_retried_check_in_creates_only_one_same_day_row(self):
        first = self._check_in()
        second = self._check_in()

        self.assertEqual(first, 201)
        self.assertEqual(second, 400)
        self.assertEqual(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).count(),
            1,
        )

    def test_simultaneous_check_in_is_serialized_by_employee_row_lock(self):
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self._check_in, barrier) for _ in range(2)]
            statuses = sorted(future.result(timeout=30) for future in futures)

        self.assertEqual(statuses, [201, 400])
        self.assertEqual(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).count(),
            1,
        )
