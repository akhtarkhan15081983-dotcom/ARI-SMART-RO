from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0011_add_calling_designation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="department",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="grade",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="job_title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="reporting_manager",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="direct_reports",
                to="employees.employeeprofile",
            ),
        ),
        migrations.CreateModel(
            name="EmployeeCareerMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("movement_type", models.CharField(
                    choices=[
                        ("PROMOTION", "Promotion"),
                        ("DESIGNATION_CHANGE", "Designation Change"),
                        ("SALARY_REVISION", "Salary Revision"),
                        ("TRANSFER", "Department Transfer"),
                        ("MANAGER_CHANGE", "Reporting Manager Change"),
                        ("DEMOTION", "Demotion"),
                        ("OTHER", "Other"),
                    ],
                    max_length=24,
                )),
                ("effective_date", models.DateField(default=django.utils.timezone.localdate)),
                ("old_designation", models.CharField(blank=True, default="", max_length=20)),
                ("new_designation", models.CharField(blank=True, default="", max_length=20)),
                ("old_job_title", models.CharField(blank=True, default="", max_length=120)),
                ("new_job_title", models.CharField(blank=True, default="", max_length=120)),
                ("old_department", models.CharField(blank=True, default="", max_length=100)),
                ("new_department", models.CharField(blank=True, default="", max_length=100)),
                ("old_grade", models.CharField(blank=True, default="", max_length=50)),
                ("new_grade", models.CharField(blank=True, default="", max_length=50)),
                ("old_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("new_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("reason", models.CharField(max_length=500)),
                ("status", models.CharField(
                    choices=[("DRAFT", "Draft"), ("APPROVED", "Approved"), ("CANCELLED", "Cancelled")],
                    default="DRAFT",
                    max_length=12,
                )),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("approved_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="approved_career_movements",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="created_career_movements",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("employee", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="career_movements",
                    to="employees.employeeprofile",
                )),
                ("new_reporting_manager", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="career_movements_as_new_manager",
                    to="employees.employeeprofile",
                )),
                ("old_reporting_manager", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="career_movements_as_old_manager",
                    to="employees.employeeprofile",
                )),
            ],
            options={"ordering": ["-effective_date", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="employeecareermovement",
            index=models.Index(fields=["employee", "effective_date"], name="emp_career_emp_date_idx"),
        ),
        migrations.AddIndex(
            model_name="employeecareermovement",
            index=models.Index(fields=["status", "effective_date"], name="emp_career_status_idx"),
        ),
    ]
