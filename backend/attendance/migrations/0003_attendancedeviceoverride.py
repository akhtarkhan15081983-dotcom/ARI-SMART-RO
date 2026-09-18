from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0002_attendance_identity_review"),
        ("employees", "0010_employeepenalty"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendanceDeviceOverride",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_device_overrides",
                        to="employees.employeeprofile",
                    ),
                ),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="granted_attendance_device_overrides",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-date", "employee__employee_id"]},
        ),
        migrations.AddConstraint(
            model_name="attendancedeviceoverride",
            constraint=models.UniqueConstraint(
                fields=("employee", "date"),
                name="unique_employee_attendance_device_override_date",
            ),
        ),
    ]
