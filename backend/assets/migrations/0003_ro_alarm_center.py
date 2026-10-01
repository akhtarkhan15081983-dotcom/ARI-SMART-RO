# Generated manually for RO Alarm Center hardening.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0002_alter_roasset_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="roasset",
            name="alarm_monitoring_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="roasset",
            name="next_filter_change_date",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Optional planned filter-change date used by RO Alarm Center.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="roasset",
            name="output_tds_attention_level",
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    "Optional maintenance attention threshold. Crossing it creates an "
                    "attention alarm; it is not a water-safety determination."
                ),
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="ROAlarm",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "alarm_type",
                    models.CharField(
                        choices=[
                            ("SERVICE_DUE", "Service Due"),
                            ("FILTER_DUE", "Filter Change Due"),
                            ("LEAKAGE", "Leakage"),
                            ("NOISE", "Unusual Noise"),
                            ("TASTE", "Taste Change"),
                            ("TDS", "TDS Attention"),
                            ("LOW_FLOW", "Low Water Flow"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("LOW", "Low"),
                            ("NORMAL", "Normal"),
                            ("HIGH", "High"),
                            ("CRITICAL", "Critical"),
                        ],
                        default="NORMAL",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Open"),
                            ("ACKNOWLEDGED", "Acknowledged"),
                            ("RESOLVED", "Resolved"),
                        ],
                        db_index=True,
                        default="OPEN",
                        max_length=16,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("SYSTEM", "System"),
                            ("CUSTOMER", "Customer"),
                            ("ENGINEER", "Engineer"),
                            ("STAFF", "Staff"),
                        ],
                        default="SYSTEM",
                        max_length=12,
                    ),
                ),
                ("title", models.CharField(max_length=140)),
                ("message", models.TextField(blank=True, default="", max_length=1000)),
                ("observed_value", models.PositiveIntegerField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, db_index=True, null=True)),
                (
                    "dedupe_key",
                    models.CharField(
                        blank=True,
                        max_length=180,
                        null=True,
                        unique=True,
                    ),
                ),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "acknowledged_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="acknowledged_ro_alarms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_ro_alarms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "resolved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resolved_ro_alarms",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ro_asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alarms",
                        to="assets.roasset",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(
                        fields=["ro_asset", "status", "alarm_type"],
                        name="asset_alarm_state_idx",
                    ),
                    models.Index(
                        fields=["status", "due_date"],
                        name="asset_alarm_due_idx",
                    ),
                ],
            },
        ),
    ]
