import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("service", "0002_service_company"),
        ("products", "0005_romodel_sale_rent_availability"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicepart",
            name="action",
            field=models.CharField(
                choices=[
                    ("USED", "Part Used"),
                    ("REPLACED", "Part Replaced"),
                    ("CLEANED", "Part Cleaned"),
                    ("INSPECTED", "Part Inspected"),
                ],
                default="USED",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="servicepart",
            name="verification_method",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.CreateModel(
            name="ServiceIntervalPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("configuration_key", models.CharField(blank=True, default="", max_length=80)),
                ("interval_days", models.PositiveIntegerField()),
                ("due_soon_days", models.PositiveIntegerField(default=30)),
                ("reminder_days", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ro_service_interval_policies", to="tenancy.company")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="service_interval_policies", to="partmaster.partmaster")),
                ("ro_model", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="service_interval_policies", to="products.romodel")),
            ],
            options={
                "ordering": ["part__name", "ro_model__model_name", "configuration_key"],
            },
        ),
        migrations.CreateModel(
            name="PartServiceCycleAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cycle_started_at", models.DateTimeField()),
                ("old_due_date", models.DateField(blank=True, null=True)),
                ("new_due_date", models.DateField(blank=True, null=True)),
                ("verification_method", models.CharField(blank=True, max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_service_cycle_audits", to="tenancy.company")),
                ("engineer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_service_cycle_audits", to="employees.employeeprofile")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="service_cycle_audits", to="partmaster.partmaster")),
                ("ro_asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_service_cycle_audits", to="assets.roasset")),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_cycle_audits", to="service.service")),
                ("source_service_part", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="cycle_audit", to="service.servicepart")),
            ],
            options={
                "ordering": ["-cycle_started_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="serviceintervalpolicy",
            constraint=models.UniqueConstraint(
                fields=("company", "part", "ro_model", "configuration_key"),
                name="uniq_ro_service_interval_policy",
                nulls_distinct=False,
            ),
        ),
    ]
