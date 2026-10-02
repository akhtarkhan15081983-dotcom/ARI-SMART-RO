from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("employees", "0025_one_time_device_migration_reset"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeHrLifecycle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employment_type", models.CharField(choices=[("PROBATION", "Probation"), ("PERMANENT", "Permanent"), ("CONTRACT", "Contract"), ("TRAINEE", "Trainee")], default="PROBATION", max_length=16)),
                ("employment_status", models.CharField(choices=[("ONBOARDING", "Onboarding"), ("PROBATION", "Probation"), ("CONFIRMED", "Confirmed"), ("NOTICE", "Notice Period"), ("SUSPENDED", "Suspended"), ("SEPARATED", "Separated"), ("INACTIVE", "Inactive")], default="ONBOARDING", max_length=16)),
                ("hr_stage", models.CharField(choices=[("CREATED", "Created"), ("PROFILE_PENDING", "Profile Pending"), ("DOCUMENT_PENDING", "Document Pending"), ("SECURITY_PENDING", "Security Pending"), ("TRAINING_PENDING", "Training Pending"), ("HR_REVIEW", "HR Review"), ("READY", "Ready for Duty")], default="CREATED", max_length=24)),
                ("work_location", models.CharField(blank=True, default="", max_length=120)),
                ("probation_months", models.PositiveSmallIntegerField(default=3)),
                ("probation_start_date", models.DateField(blank=True, null=True)),
                ("confirmation_due_date", models.DateField(blank=True, null=True)),
                ("confirmed_at", models.DateField(blank=True, null=True)),
                ("manager_review_status", models.CharField(default="PENDING", max_length=16)),
                ("manager_review_note", models.TextField(blank=True, default="")),
                ("hr_review_status", models.CharField(default="PENDING", max_length=16)),
                ("hr_review_note", models.TextField(blank=True, default="")),
                ("policy_acknowledged", models.BooleanField(default=False)),
                ("sop_acknowledged", models.BooleanField(default=False)),
                ("safety_training_acknowledged", models.BooleanField(default=False)),
                ("payroll_details_complete", models.BooleanField(default=False)),
                ("role_access_assigned", models.BooleanField(default=False)),
                ("joining_checklist", models.JSONField(blank=True, default=dict)),
                ("bank_details", models.JSONField(blank=True, default=dict)),
                ("compensation_profile", models.JSONField(blank=True, default=dict)),
                ("hr_override_ready", models.BooleanField(default=False)),
                ("hr_override_reason", models.CharField(blank=True, default="", max_length=500)),
                ("notice_start_date", models.DateField(blank=True, null=True)),
                ("last_working_date", models.DateField(blank=True, null=True)),
                ("separation_type", models.CharField(blank=True, default="", max_length=40)),
                ("exit_reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="hr_lifecycle", to="employees.employeeprofile")),
            ],
            options={"ordering": ["employee__employee_id"]},
        ),
        migrations.CreateModel(
            name="EmployeeHrLifecycleEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=40)),
                ("effective_date", models.DateField(default=django.utils.timezone.localdate)),
                ("from_status", models.CharField(blank=True, default="", max_length=40)),
                ("to_status", models.CharField(blank=True, default="", max_length=40)),
                ("note", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_hr_lifecycle_events", to=settings.AUTH_USER_MODEL)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="hr_lifecycle_events", to="employees.employeeprofile")),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
    ]
