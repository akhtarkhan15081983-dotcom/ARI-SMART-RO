from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0020_expand_corporate_training_content"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeDeviceHealth",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_id", models.CharField(blank=True, default="", max_length=64)),
                ("platform", models.CharField(default="ANDROID", max_length=20)),
                ("app_version", models.CharField(blank=True, default="", max_length=32)),
                ("app_build", models.CharField(blank=True, default="", max_length=24)),
                ("os_version", models.CharField(blank=True, default="", max_length=80)),
                ("android_sdk", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("manufacturer", models.CharField(blank=True, default="", max_length=80)),
                ("model", models.CharField(blank=True, default="", max_length=120)),
                ("low_memory_device", models.BooleanField(default=False)),
                ("memory_class_mb", models.PositiveIntegerField(blank=True, null=True)),
                ("total_memory_mb", models.PositiveIntegerField(blank=True, null=True)),
                ("location_service_enabled", models.BooleanField(default=False)),
                ("location_permission", models.CharField(blank=True, default="", max_length=24)),
                ("background_location_granted", models.BooleanField(default=False)),
                ("notification_permission_granted", models.BooleanField(default=False)),
                ("battery_optimization_ignored", models.BooleanField(default=False)),
                ("live_location_tracking", models.BooleanField(default=False)),
                ("pending_job_actions", models.PositiveIntegerField(default=0)),
                ("pending_location_points", models.PositiveIntegerField(default=0)),
                ("last_error", models.CharField(blank=True, default="", max_length=500)),
                ("reported_at", models.DateTimeField(auto_now=True)),
                ("employee", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="device_health", to="employees.employeeprofile")),
            ],
            options={"ordering": ["-reported_at"]},
        ),
        migrations.AddIndex(
            model_name="employeedevicehealth",
            index=models.Index(fields=["reported_at"], name="emp_devhealth_seen_idx"),
        ),
    ]
