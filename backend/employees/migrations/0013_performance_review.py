from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0012_corporate_career_movements"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PerformanceReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("goals_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("attendance_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("service_quality_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("customer_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("sales_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("overall_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("strengths", models.TextField(blank=True, default="")),
                ("improvement_plan", models.TextField(blank=True, default="")),
                ("comments", models.TextField(blank=True, default="")),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT", "Draft"),
                        ("SUBMITTED", "Submitted"),
                        ("FINAL", "Final"),
                        ("ACKNOWLEDGED", "Acknowledged"),
                    ],
                    default="DRAFT",
                    max_length=16,
                )),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="performance_reviews",
                    to="employees.employeeprofile",
                )),
                ("reviewer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="performance_reviews_given",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-period_end", "-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="performancereview",
            constraint=models.UniqueConstraint(
                fields=("employee", "period_start", "period_end"),
                name="unique_employee_performance_period",
            ),
        ),
    ]
