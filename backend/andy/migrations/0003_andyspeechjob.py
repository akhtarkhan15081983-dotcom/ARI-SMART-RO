import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("andy", "0002_andypendingaction"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(
        name="AndySpeechJob",
        fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("text", models.TextField()),
            ("status", models.CharField(choices=[("PENDING", "Pending"), ("RUNNING", "Running"), ("COMPLETED", "Completed"), ("FAILED", "Failed")], db_index=True, default="PENDING", max_length=16)),
            ("audio", models.BinaryField(blank=True, null=True)),
            ("error", models.TextField(blank=True, default="")),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="andy_speech_jobs", to=settings.AUTH_USER_MODEL)),
        ],
        options={"ordering": ["-created_at"]},
    )]
