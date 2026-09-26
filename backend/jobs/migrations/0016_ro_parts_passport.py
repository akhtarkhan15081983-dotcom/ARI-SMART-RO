from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0015_backfill_complaint_jobs"),
    ]

    operations = [
        migrations.CreateModel(
            name="ROPartsInspection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("inspection_type", models.CharField(choices=[("BASELINE", "Baseline scan"), ("VISUAL_CHECK", "Visual check"), ("REPLACEMENT", "Replacement")], default="VISUAL_CHECK", max_length=20)),
                ("source", models.CharField(choices=[("PHOTO_AI", "Photo + AI"), ("INVENTORY_JOB", "Inventory job"), ("MANUAL", "Manual confirmation")], default="PHOTO_AI", max_length=20)),
                ("status", models.CharField(choices=[("CAPTURED", "Captured"), ("ANALYZED", "Analyzed"), ("NEEDS_REVIEW", "Needs review"), ("CONFIRMED", "Confirmed")], default="CAPTURED", max_length=20)),
                ("captured_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("ai_provider", models.CharField(blank=True, default="", max_length=40)),
                ("ai_model", models.CharField(blank=True, default="", max_length=80)),
                ("ai_summary", models.TextField(blank=True, default="")),
                ("raw_ai_result", models.JSONField(blank=True, default=dict)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_ro_parts_inspections", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ro_parts_inspections", to="customers.customer")),
                ("engineer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ro_parts_inspections", to="employees.employeeprofile")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ro_parts_inspections", to="jobs.job")),
                ("ro_asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parts_inspections", to="assets.roasset")),
            ],
            options={"ordering": ["-captured_at", "-id"]},
        ),
        migrations.CreateModel(
            name="ROPartsInspectionPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="jobs/ro_parts_passport/%Y/%m/")),
                ("angle", models.CharField(blank=True, default="", max_length=30)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("inspection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="jobs.ropartsinspection")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="ROPartsObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("part_key", models.CharField(max_length=60)),
                ("part_name", models.CharField(max_length=120)),
                ("confidence", models.DecimalField(decimal_places=4, default=0, max_digits=5)),
                ("visible", models.BooleanField(default=True)),
                ("confirmed", models.BooleanField(default=False)),
                ("installed_on", models.DateField(blank=True, null=True)),
                ("date_source", models.CharField(blank=True, choices=[("BASELINE_ASSUMED", "Baseline date (actual prior replacement unknown)"), ("CARRIED_FORWARD", "Carried from previous confirmed record"), ("REPLACEMENT_CONFIRMED", "Replacement confirmed by employee"), ("INVENTORY_JOB", "Replacement verified from inventory job")], default="", max_length=30)),
                ("evidence_notes", models.CharField(blank=True, default="", max_length=250)),
                ("inspection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="observations", to="jobs.ropartsinspection")),
            ],
            options={"ordering": ["part_name", "id"]},
        ),
        migrations.AddIndex(
            model_name="ropartsinspection",
            index=models.Index(fields=["ro_asset", "captured_at"], name="jobs_ro_parts_asset_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="ropartsinspection",
            index=models.Index(fields=["customer", "captured_at"], name="jobs_ro_parts_customer_dt_idx"),
        ),
        migrations.AddIndex(
            model_name="ropartsobservation",
            index=models.Index(fields=["part_key", "confirmed"], name="jobs_ro_part_key_conf_idx"),
        ),
        migrations.AddConstraint(
            model_name="ropartsobservation",
            constraint=models.UniqueConstraint(fields=("inspection", "part_key"), name="unique_ro_part_per_inspection"),
        ),
    ]
