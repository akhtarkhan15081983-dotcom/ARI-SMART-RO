import os

from django.core.management.base import BaseCommand
from django.db import transaction

from employees.models import EmployeeProfile


class Command(BaseCommand):
    help = "One-time reset of employee face enrollment and attendance device binding."

    @transaction.atomic
    def handle(self, *args, **options):
        enabled = os.getenv("RESET_EMPLOYEE_FACE_DEVICE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not enabled:
            self.stdout.write("Employee face/device reset skipped.")
            return

        employees = EmployeeProfile.objects.all()
        count = employees.count()

        employees.update(
            photo="",
            face_enrolled_at=None,
            face_enrollment_verified=False,
            face_enrollment_allowed=False,
            attendance_device_id="",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Employee face/device reset completed for {count} employee profiles. "
                "Attendance, payroll, jobs and account data were preserved."
            )
        )
