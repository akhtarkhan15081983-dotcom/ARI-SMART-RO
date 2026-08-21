from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("andy", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AndyPendingAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action_type", models.CharField(max_length=80)),
                ("target_type", models.CharField(max_length=80)),
                ("target_id", models.CharField(max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("PENDING", "Pending confirmation"), ("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled"), ("FAILED", "Failed")], default="PENDING", max_length=16)),
                ("summary", models.CharField(max_length=240)),
                ("result", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="andy_pending_actions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="andypendingaction",
            index=models.Index(fields=["user", "status", "created_at"], name="andy_andype_user_id_9dbf21_idx"),
        ),
    ]
