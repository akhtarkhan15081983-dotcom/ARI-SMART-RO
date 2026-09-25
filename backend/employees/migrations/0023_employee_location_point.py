from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0022_employeedevicehealth"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeLocationPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("captured_at", models.DateTimeField(db_index=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="location_points", to="employees.employeeprofile")),
            ],
            options={"ordering": ["captured_at", "id"]},
        ),
        migrations.AddIndex(
            model_name="employeelocationpoint",
            index=models.Index(fields=["employee", "captured_at"], name="emp_loc_employee_time_idx"),
        ),
        migrations.AddConstraint(
            model_name="employeelocationpoint",
            constraint=models.UniqueConstraint(fields=("employee", "captured_at", "latitude", "longitude"), name="unique_employee_location_point"),
        ),
    ]
