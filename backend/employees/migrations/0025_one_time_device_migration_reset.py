from django.db import migrations
from django.utils import timezone


def reset_all_employee_devices(apps, schema_editor):
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")
    User = apps.get_model("accounts", "User")
    AttendanceDeviceOverride = apps.get_model("attendance", "AttendanceDeviceOverride")

    now = timezone.now()

    employee_user_ids = list(
        EmployeeProfile.objects.exclude(user_id=None).values_list("user_id", flat=True)
    )

    User.objects.filter(id__in=employee_user_ids).exclude(
        role__in=["ADMIN", "CUSTOMER"]
    ).update(
        previous_login_device_id="",
        active_login_device_id="",
        login_device_bound_at=None,
        login_device_reset_at=now,
    )

    EmployeeProfile.objects.update(
        attendance_device_id="",
        face_enrollment_allowed=True,
        face_enrollment_verified=False,
        is_online=False,
    )

    AttendanceDeviceOverride.objects.filter(is_active=True).update(is_active=False)


def reverse_noop(apps, schema_editor):
    # Device bindings are security state and cannot be reconstructed safely.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_systemauditevent"),
        ("attendance", "0004_work_hours_overtime"),
        ("employees", "0024_reset_faizan_device_binding"),
    ]

    operations = [
        migrations.RunPython(reset_all_employee_devices, reverse_noop),
    ]
