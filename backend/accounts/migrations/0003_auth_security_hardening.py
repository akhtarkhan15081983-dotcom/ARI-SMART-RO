from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_phoneotp")]

    operations = [
        migrations.AddField(model_name="user", name="failed_login_attempts", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="user", name="locked_until", field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(
            name="AuthSecurityEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("LOGIN_SUCCESS", "Login Success"), ("LOGIN_FAILED", "Login Failed"), ("ACCOUNT_LOCKED", "Account Locked"), ("OTP_VERIFIED", "OTP Verified")], max_length=24)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("device_id", models.CharField(blank=True, default="", max_length=64)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="security_events", to="accounts.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
