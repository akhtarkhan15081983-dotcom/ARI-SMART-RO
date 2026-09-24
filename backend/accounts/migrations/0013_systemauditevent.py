from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_alter_authsecurityevent_event_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=80)),
                ("entity_type", models.CharField(max_length=80)),
                ("entity_id", models.CharField(blank=True, default="", max_length=120)),
                ("company_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("company_name", models.CharField(blank=True, default="", max_length=180)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("device_id", models.CharField(blank=True, default="", max_length=128)),
                ("reason", models.CharField(blank=True, default="", max_length=500)),
                ("before_state", models.JSONField(blank=True, default=dict)),
                ("after_state", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="system_audit_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="systemauditevent",
            index=models.Index(fields=["company_id", "created_at"], name="audit_company_time_idx"),
        ),
        migrations.AddIndex(
            model_name="systemauditevent",
            index=models.Index(fields=["action", "created_at"], name="audit_action_time_idx"),
        ),
        migrations.AddIndex(
            model_name="systemauditevent",
            index=models.Index(fields=["entity_type", "entity_id", "created_at"], name="audit_entity_time_idx"),
        ),
    ]
