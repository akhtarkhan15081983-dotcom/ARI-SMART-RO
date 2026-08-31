from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("employees", "0005_employeeprofile_face_enrollment_allowed"),
        ("jobs", "0011_job_otp_attempts_job_otp_created_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkScheduleOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_key", models.CharField(db_index=True, max_length=80, unique=True)),
                ("scheduled_date", models.DateTimeField()),
                ("previous_date", models.DateTimeField(blank=True, null=True)),
                ("reason", models.CharField(blank=True, max_length=250)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="work_schedule_overrides", to="employees.employeeprofile")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="work_schedule_changes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["scheduled_date", "event_key"]},
        ),
    ]
