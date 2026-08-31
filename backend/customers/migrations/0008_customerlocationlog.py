from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0007_customer_user"),
        ("employees", "0005_employeeprofile_face_enrollment_allowed"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerLocationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("accuracy", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("source", models.CharField(choices=[("WORK_CALENDAR", "Work Calendar"), ("WORK_ROUTE", "Work Route")], default="WORK_CALENDAR", max_length=20)),
                ("captured_at", models.DateTimeField(auto_now_add=True)),
                ("captured_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_locations_captured", to="employees.employeeprofile")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="location_logs", to="customers.customer")),
            ],
            options={"ordering": ["-captured_at"]},
        ),
    ]
