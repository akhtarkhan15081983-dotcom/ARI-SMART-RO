from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0029_phase2_ats_interviews_offers"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hrletter",
            name="letter_type",
            field=models.CharField(
                choices=[
                    ("OFFER", "Offer"),
                    ("APPOINTMENT", "Appointment"),
                    ("CONFIRMATION", "Confirmation"),
                    ("PROMOTION", "Promotion"),
                    ("INCREMENT", "Increment"),
                    ("WARNING", "Warning"),
                    ("NOTICE", "Notice"),
                    ("TRANSFER", "Transfer"),
                    ("SEPARATION", "Separation"),
                    ("EXPERIENCE", "Experience"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="CorporateHrAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_type", models.CharField(max_length=40)),
                ("entity_id", models.PositiveBigIntegerField()),
                ("action", models.CharField(max_length=40)),
                ("from_status", models.CharField(blank=True, default="", max_length=40)),
                ("to_status", models.CharField(blank=True, default="", max_length=40)),
                ("reason", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corporate_hr_audit_events", to="tenancy.company")),
                ("performed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corporate_hr_audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="HrLetterTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("letter_type", models.CharField(choices=[("APPOINTMENT", "Appointment"), ("CONFIRMATION", "Confirmation"), ("PROMOTION", "Promotion"), ("INCREMENT", "Increment"), ("WARNING", "Warning"), ("NOTICE", "Notice / Show Cause"), ("TRANSFER", "Transfer"), ("SEPARATION", "Separation / Relieving"), ("EXPERIENCE", "Experience")], max_length=20)),
                ("subject_template", models.CharField(max_length=200)),
                ("body_template", models.TextField()),
                ("version", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="hr_letter_templates", to="tenancy.company")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_hr_letter_templates", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="updated_hr_letter_templates", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["letter_type", "name", "-version"]},
        ),
        migrations.CreateModel(
            name="BgvPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mandatory_before_ready", models.BooleanField(default=False)),
                ("required_checks", models.JSONField(blank=True, default=list)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="bgv_policy", to="tenancy.company")),
                ("updated_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="updated_bgv_policies", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="BackgroundVerificationCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("overall_status", models.CharField(choices=[("NOT_STARTED", "Not Started"), ("IN_PROGRESS", "In Progress"), ("CLEAR", "Clear"), ("CONDITIONAL", "Conditional"), ("FAILED", "Failed"), ("WAIVED", "Waived")], default="NOT_STARTED", max_length=20)),
                ("decision_note", models.TextField(blank=True, default="")),
                ("waiver_reason", models.TextField(blank=True, default="")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("application", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bgv_cases", to="employees.candidateapplication")),
                ("candidate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bgv_cases", to="employees.candidate")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bgv_cases", to="tenancy.company")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_bgv_cases", to=settings.AUTH_USER_MODEL)),
                ("decided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="decided_bgv_cases", to=settings.AUTH_USER_MODEL)),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bgv_cases", to="employees.employeeprofile")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="HrLetterWorkflow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("letter_type", models.CharField(choices=[("APPOINTMENT", "Appointment"), ("CONFIRMATION", "Confirmation"), ("PROMOTION", "Promotion"), ("INCREMENT", "Increment"), ("WARNING", "Warning"), ("NOTICE", "Notice / Show Cause"), ("TRANSFER", "Transfer"), ("SEPARATION", "Separation / Relieving"), ("EXPERIENCE", "Experience")], max_length=20)),
                ("subject", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("effective_date", models.DateField()),
                ("context", models.JSONField(blank=True, default=dict)),
                ("lifecycle_event_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("career_movement_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("PENDING_APPROVAL", "Pending Approval"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("ISSUED", "Issued")], default="DRAFT", max_length=24)),
                ("approval_note", models.TextField(blank=True, default="")),
                ("rejection_reason", models.TextField(blank=True, default="")),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_hr_letter_workflows", to=settings.AUTH_USER_MODEL)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="hr_letter_workflows", to="tenancy.company")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_hr_letter_workflows", to=settings.AUTH_USER_MODEL)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="hr_letter_workflows", to="employees.employeeprofile")),
                ("issued_letter", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="workflow_source", to="employees.hrletter")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="letter_workflows", to="employees.hrlettertemplate")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="HrLetterAcknowledgement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("ACKNOWLEDGED", "Acknowledged"), ("DECLINED", "Declined")], max_length=16)),
                ("note", models.TextField(blank=True, default="")),
                ("evidence", models.JSONField(blank=True, default=dict)),
                ("responded_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="hr_letter_acknowledgements", to=settings.AUTH_USER_MODEL)),
                ("letter", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="acknowledgement", to="employees.hrletter")),
            ],
        ),
        migrations.CreateModel(
            name="BackgroundVerificationCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("check_type", models.CharField(choices=[("IDENTITY", "Identity"), ("ADDRESS", "Address"), ("EDUCATION", "Education"), ("EMPLOYMENT", "Previous Employment"), ("CRIMINAL_POLICE", "Criminal / Police"), ("REFERENCE", "Reference Check")], max_length=24)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"), ("VERIFIED", "Verified"), ("FAILED", "Failed"), ("NOT_APPLICABLE", "Not Applicable")], default="PENDING", max_length=20)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("evidence_reference", models.CharField(blank=True, default="", max_length=300)),
                ("notes", models.TextField(blank=True, default="")),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="checks", to="employees.backgroundverificationcase")),
                ("verifier", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="bgv_checks_verified", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["check_type"]},
        ),
        migrations.AddConstraint(
            model_name="hrlettertemplate",
            constraint=models.UniqueConstraint(fields=("company", "name", "version"), name="hr2_letter_tpl_company_name_ver_uniq"),
        ),
        migrations.AddIndex(
            model_name="hrlettertemplate",
            index=models.Index(fields=["company", "letter_type", "is_active"], name="hr2_letter_tpl_company_idx"),
        ),
        migrations.AddConstraint(
            model_name="backgroundverificationcase",
            constraint=models.CheckConstraint(condition=models.Q(("candidate__isnull", False), ("employee__isnull", False), _connector="OR"), name="hr2_bgv_case_has_subject"),
        ),
        migrations.AddConstraint(
            model_name="backgroundverificationcase",
            constraint=models.UniqueConstraint(condition=models.Q(("application__isnull", False)), fields=("application",), name="hr2_bgv_unique_application"),
        ),
        migrations.AddConstraint(
            model_name="backgroundverificationcase",
            constraint=models.UniqueConstraint(condition=models.Q(("employee__isnull", False)), fields=("employee",), name="hr2_bgv_unique_employee"),
        ),
        migrations.AddIndex(
            model_name="backgroundverificationcase",
            index=models.Index(fields=["company", "overall_status"], name="hr2_bgv_company_status_idx"),
        ),
        migrations.AddIndex(
            model_name="hrletterworkflow",
            index=models.Index(fields=["company", "status", "letter_type"], name="hr2_letter_flow_company_idx"),
        ),
        migrations.AddIndex(
            model_name="hrletterworkflow",
            index=models.Index(fields=["employee", "status"], name="hr2_letter_flow_employee_idx"),
        ),
        migrations.AddConstraint(
            model_name="backgroundverificationcheck",
            constraint=models.UniqueConstraint(fields=("case", "check_type"), name="hr2_bgv_case_check_type_uniq"),
        ),
        migrations.AddIndex(
            model_name="backgroundverificationcheck",
            index=models.Index(fields=["case", "status"], name="hr2_bgv_check_case_status_idx"),
        ),
        migrations.AddIndex(
            model_name="corporatehrauditevent",
            index=models.Index(fields=["company", "entity_type", "entity_id"], name="hr2_corp_audit_entity_idx"),
        ),
    ]
