from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_auth_security_hardening")]

    operations = [
        migrations.CreateModel(
            name="SmsGatewayDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_id", models.CharField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("secret_hash", models.CharField(max_length=64)),
                ("phone_number", models.CharField(blank=True, default="", max_length=15)),
                ("is_active", models.BooleanField(default=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="SimVerificationChallenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(db_index=True, max_length=64)),
                ("poll_secret_hash", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("VERIFIED", "Verified"), ("EXPIRED", "Expired"), ("CANCELLED", "Cancelled")], default="PENDING", max_length=12)),
                ("expires_at", models.DateTimeField()),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sim_verification_challenges", to="accounts.user")),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_challenges", to="accounts.smsgatewaydevice")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SmsGatewaySubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nonce", models.CharField(max_length=64, unique=True)),
                ("sender_phone", models.CharField(max_length=15)),
                ("message_fingerprint", models.CharField(max_length=64)),
                ("accepted", models.BooleanField(default=False)),
                ("result_code", models.CharField(max_length=40)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("gateway", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submissions", to="accounts.smsgatewaydevice")),
            ],
            options={"ordering": ["-received_at"]},
        ),
    ]
