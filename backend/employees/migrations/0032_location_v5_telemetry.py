from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0031_phase2_employee_lifecycle"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeelocationpoint",
            name="accuracy_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="source",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="speed_mps",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="heading_degrees",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="motion_state",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="quality_label",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="client_point_id",
            field=models.CharField(blank=True, max_length=96, null=True),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="client_sequence",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="altitude_m",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeelocationpoint",
            name="client_platform",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddIndex(
            model_name="employeelocationpoint",
            index=models.Index(
                fields=["employee", "client_sequence"],
                name="emp_loc_employee_seq_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="employeelocationpoint",
            constraint=models.UniqueConstraint(
                condition=models.Q(client_point_id__isnull=False),
                fields=("employee", "client_point_id"),
                name="unique_employee_client_point",
            ),
        ),
    ]
