from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0030_phase2_hr_letters_bgv"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeLifecycleAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_type", models.CharField(choices=[("PROBATION_REVIEW", "Probation Review"), ("PROBATION_EXTENSION", "Probation Extension"), ("CONFIRMATION", "Confirmation"), ("PROMOTION", "Promotion"), ("INCREMENT", "Increment"), ("TRANSFER", "Transfer"), ("SEPARATION", "Separation")], max_length=24)),
                ("effective_date", models.DateField()),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("MANAGER_REVIEW", "Manager Review"), ("HR_REVIEW", "HR Review"), ("PENDING_APPROVAL", "Pending Approval"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("APPLIED", "Applied"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=24)),
                ("reason", models.TextField()), ("proposed_changes", models.JSONField(blank=True, default=dict)), ("snapshot_before", models.JSONField(blank=True, default=dict)), ("manager_assessment", models.JSONField(blank=True, default=dict)), ("hr_assessment", models.JSONField(blank=True, default=dict)),
                ("manager_reviewed_at", models.DateTimeField(blank=True, null=True)), ("hr_reviewed_at", models.DateTimeField(blank=True, null=True)), ("approved_at", models.DateTimeField(blank=True, null=True)), ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("career_movement_id", models.PositiveBigIntegerField(blank=True, null=True)), ("letter_workflow_id", models.PositiveBigIntegerField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employee_lifecycle_actions", to="tenancy.company")),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="phase2_lifecycle_actions", to="employees.employeeprofile")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_employee_lifecycle_actions", to=settings.AUTH_USER_MODEL)),
                ("manager_reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="manager_reviewed_lifecycle_actions", to=settings.AUTH_USER_MODEL)),
                ("hr_reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="hr_reviewed_lifecycle_actions", to=settings.AUTH_USER_MODEL)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_employee_lifecycle_actions", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-effective_date", "-created_at"]}),
        migrations.CreateModel(
            name="ExitCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("separation_type", models.CharField(choices=[("RESIGNATION", "Resignation"), ("TERMINATION", "Termination"), ("RETIREMENT", "Retirement"), ("CONTRACT_COMPLETION", "Contract Completion"), ("ABSCONDING", "Absconding")], max_length=24)),
                ("resignation_date", models.DateField(blank=True, null=True)), ("notice_days", models.PositiveSmallIntegerField(default=0)), ("proposed_last_working_date", models.DateField()), ("approved_last_working_date", models.DateField(blank=True, null=True)), ("notice_waiver_days", models.PositiveSmallIntegerField(default=0)), ("notice_recovery_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)), ("reason", models.TextField()),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("NOTICE", "Notice"), ("CLEARANCE", "Clearance"), ("PENDING_APPROVAL", "Pending Approval"), ("APPROVED", "Approved"), ("SEPARATED", "Separated"), ("CANCELLED", "Cancelled")], default="DRAFT", max_length=24)),
                ("final_settlement_ready", models.BooleanField(default=False)), ("approved_at", models.DateTimeField(blank=True, null=True)), ("separated_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employee_exit_cases", to="tenancy.company")), ("employee", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="phase2_exit_case", to="employees.employeeprofile")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_exit_cases", to=settings.AUTH_USER_MODEL)), ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_exit_cases", to=settings.AUTH_USER_MODEL)),
            ]),
        migrations.CreateModel(
            name="ExitClearance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("clearance_type", models.CharField(choices=[("ASSET", "Company Assets"), ("FINANCE", "Finance / Payroll"), ("MANAGER", "Manager"), ("HR", "HR")], max_length=16)), ("status", models.CharField(choices=[("PENDING", "Pending"), ("CLEARED", "Cleared"), ("BLOCKED", "Blocked"), ("WAIVED", "Waived")], default="PENDING", max_length=16)), ("note", models.TextField(blank=True, default="")), ("evidence", models.JSONField(blank=True, default=dict)), ("waiver_reason", models.TextField(blank=True, default="")), ("reviewed_at", models.DateTimeField(blank=True, null=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("exit_case", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="clearances", to="employees.exitcase")), ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_exit_clearances", to=settings.AUTH_USER_MODEL)),
            ]),
        migrations.CreateModel(
            name="EmployeeLifecycleAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("entity_type", models.CharField(max_length=30)), ("entity_id", models.PositiveBigIntegerField()), ("action", models.CharField(max_length=40)), ("from_status", models.CharField(blank=True, default="", max_length=30)), ("to_status", models.CharField(blank=True, default="", max_length=30)), ("reason", models.TextField(blank=True, default="")), ("metadata", models.JSONField(blank=True, default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employee_lifecycle_audits", to="tenancy.company")), ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="phase2_lifecycle_audits", to="employees.employeeprofile")), ("performed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="employee_lifecycle_audits", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-created_at"]}),
        migrations.AddIndex(model_name="employeelifecycleaction", index=models.Index(fields=["company", "status", "action_type"], name="hr2_life_company_queue_idx")),
        migrations.AddIndex(model_name="employeelifecycleaction", index=models.Index(fields=["employee", "effective_date"], name="hr2_life_employee_date_idx")),
        migrations.AddIndex(model_name="exitcase", index=models.Index(fields=["company", "status"], name="hr2_exit_company_status_idx")),
        migrations.AddConstraint(model_name="exitclearance", constraint=models.UniqueConstraint(fields=("exit_case", "clearance_type"), name="hr2_exit_clearance_type_uniq")),
        migrations.AddIndex(model_name="employeelifecycleaudit", index=models.Index(fields=["company", "employee", "created_at"], name="hr2_life_audit_emp_idx")),
    ]
