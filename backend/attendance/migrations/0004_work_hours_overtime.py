from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def backfill_regular_hours(apps, schema_editor):
    Attendance = apps.get_model("attendance", "Attendance")
    for row in Attendance.objects.all().iterator():
        row.regular_working_hours = row.working_hours or 0
        if row.check_in and row.check_out:
            row.regular_shift_end_at = row.check_out
        row.checkout_reason = "MANUAL" if row.check_out else ""
        row.save(update_fields=[
            "regular_working_hours",
            "regular_shift_end_at",
            "checkout_reason",
        ])


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0003_attendancedeviceoverride"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="attendance",
            name="regular_shift_end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendance",
            name="regular_working_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="attendance",
            name="overtime_working_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="attendance",
            name="auto_checked_out",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="attendance",
            name="checkout_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not checked out"),
                    ("MANUAL", "Manual checkout"),
                    ("AUTO_8_HOURS", "Automatic regular shift checkout"),
                ],
                default="",
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="OvertimeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_hours", models.DecimalField(decimal_places=2, default=1, max_digits=4)),
                ("approved_hours", models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ("reason", models.CharField(max_length=500)),
                ("status", models.CharField(choices=[
                    ("PENDING", "Pending admin approval"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                    ("COMPLETED", "Completed"),
                    ("CANCELLED", "Cancelled"),
                ], default="PENDING", max_length=12)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.CharField(blank=True, default="", max_length=300)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("planned_end_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("end_reason", models.CharField(blank=True, choices=[
                    ("", "Not ended"),
                    ("MANUAL", "Employee ended overtime"),
                    ("AUTO_APPROVED_LIMIT", "Approved overtime limit reached"),
                ], default="", max_length=24)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("attendance", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="overtime_request", to="attendance.attendance")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_overtime_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-requested_at"]},
        ),
        migrations.RunPython(backfill_regular_hours, migrations.RunPython.noop),
    ]
