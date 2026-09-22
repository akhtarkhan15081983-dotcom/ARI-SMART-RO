from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientErrorEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("company_name", models.CharField(blank=True, default="", max_length=180)),
                ("device_id", models.CharField(blank=True, default="", max_length=128)),
                ("platform", models.CharField(blank=True, default="", max_length=24)),
                ("app_version", models.CharField(blank=True, default="", max_length=32)),
                ("app_build", models.CharField(blank=True, default="", max_length=24)),
                ("error_type", models.CharField(blank=True, default="", max_length=120)),
                ("message", models.CharField(max_length=1000)),
                ("stack", models.TextField(blank=True, default="")),
                ("context", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="client_error_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="clienterrorevent",
            index=models.Index(fields=["company_id", "created_at"], name="clienterr_company_time_idx"),
        ),
        migrations.AddIndex(
            model_name="clienterrorevent",
            index=models.Index(fields=["error_type", "created_at"], name="clienterr_type_time_idx"),
        ),
    ]
