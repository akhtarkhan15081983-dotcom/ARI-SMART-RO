from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("employees", "0005_employeeprofile_face_enrollment_allowed")]
    operations = [
        migrations.CreateModel(name="HRPolicy", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("office_start_time", models.TimeField(default="10:00")), ("daily_work_hours", models.DecimalField(decimal_places=2, default=8, max_digits=4)),
            ("late_penalty_amount", models.DecimalField(decimal_places=2, default=50, max_digits=8)), ("half_day_cutoff", models.TimeField(default="12:00")),
            ("monthly_paid_leaves", models.PositiveSmallIntegerField(default=2)), ("monthly_paid_half_days", models.PositiveSmallIntegerField(default=2)),
            ("leave_notice_days", models.PositiveSmallIntegerField(default=1)), ("rent_installation_monthly_incentive", models.DecimalField(decimal_places=2, default=50, max_digits=8)),
            ("rent_installation_incentive_months", models.PositiveSmallIntegerField(default=12)), ("sale_installation_incentive", models.DecimalField(decimal_places=2, default=500, max_digits=8)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="LeaveRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("leave_type", models.CharField(choices=[("FULL_DAY", "Full Day"), ("HALF_DAY", "Half Day")], max_length=12)),
            ("start_date", models.DateField()), ("end_date", models.DateField()), ("reason", models.TextField(max_length=500)),
            ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], default="PENDING", max_length=12)),
            ("is_paid", models.BooleanField(default=False)), ("reviewed_at", models.DateTimeField(blank=True, null=True)), ("review_note", models.CharField(blank=True, default="", max_length=300)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="leave_requests", to="employees.employeeprofile")),
            ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_leaves", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-start_date", "-created_at"]}),
        migrations.CreateModel(name="PayrollRecord", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("payroll_month", models.DateField(help_text="First day of payroll month")),
            ("base_salary", models.DecimalField(decimal_places=2, default=0, max_digits=12)), ("payable_base", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("late_days", models.PositiveIntegerField(default=0)), ("late_penalty", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ("half_day_deduction", models.DecimalField(decimal_places=2, default=0, max_digits=10)), ("absence_deduction", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ("overtime_hours", models.DecimalField(decimal_places=2, default=0, max_digits=8)), ("overtime_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ("rent_incentive", models.DecimalField(decimal_places=2, default=0, max_digits=10)), ("sale_incentive", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ("other_earnings", models.DecimalField(decimal_places=2, default=0, max_digits=10)), ("other_deductions", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ("net_salary", models.DecimalField(decimal_places=2, default=0, max_digits=12)), ("calculation_snapshot", models.JSONField(blank=True, default=dict)),
            ("status", models.CharField(choices=[("DRAFT", "Draft"), ("APPROVED", "Approved"), ("PAID", "Paid")], default="DRAFT", max_length=10)),
            ("approved_at", models.DateTimeField(blank=True, null=True)), ("paid_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_payrolls", to=settings.AUTH_USER_MODEL)),
            ("employee", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payroll_records", to="employees.employeeprofile")),
        ], options={"ordering": ["-payroll_month", "employee__employee_id"]}),
        migrations.AddConstraint(model_name="payrollrecord", constraint=models.UniqueConstraint(fields=("employee", "payroll_month"), name="unique_employee_payroll_month")),
        migrations.CreateModel(name="EmployeeDocument", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("document_type", models.CharField(max_length=50)),
            ("document_number", models.CharField(blank=True, default="", max_length=100)), ("file", models.FileField(blank=True, null=True, upload_to="employees/documents/")),
            ("expiry_date", models.DateField(blank=True, null=True)), ("verified", models.BooleanField(default=False)), ("uploaded_at", models.DateTimeField(auto_now_add=True)),
            ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hr_documents", to="employees.employeeprofile")),
        ]),
    ]
