from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0012_workscheduleoverride"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientActionReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_id", models.CharField(max_length=160)),
                ("action_type", models.CharField(max_length=40)),
                ("response_status", models.PositiveSmallIntegerField(default=200)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="client_action_receipts", to="jobs.job")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="client_action_receipts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="clientactionreceipt",
            constraint=models.UniqueConstraint(fields=("user", "action_id"), name="unique_client_action_per_user"),
        ),
        migrations.AddIndex(
            model_name="clientactionreceipt",
            index=models.Index(fields=["user", "action_type", "created_at"], name="jobs_client_user_id_73f6ff_idx"),
        ),
    ]
