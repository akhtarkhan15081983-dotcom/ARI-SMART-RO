from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_job_otp_admin_view_event"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authsecurityevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("LOGIN_SUCCESS", "Login Success"),
                    ("LOGIN_FAILED", "Login Failed"),
                    ("ACCOUNT_LOCKED", "Account Locked"),
                    ("OTP_VERIFIED", "OTP Verified"),
                    ("JOB_OTP_ADMIN_VIEWED", "Job OTP Admin Viewed"),
                    ("PASSWORD_RESET_REQUESTED", "Password Reset Requested"),
                    ("PASSWORD_RESET_APPROVED", "Password Reset Approved"),
                    ("PASSWORD_RESET_REJECTED", "Password Reset Rejected"),
                    ("PASSWORD_RESET_COMPLETED", "Password Reset Completed"),
                ],
                max_length=24,
            ),
        ),
        migrations.CreateModel(
            name="PasswordResetRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"),
                        ("APPROVED", "Approved"),
                        ("REJECTED", "Rejected"),
                        ("USED", "Used"),
                        ("EXPIRED", "Expired"),
                    ],
                    default="PENDING",
                    max_length=12,
                )),
                ("requested_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("requested_device_id", models.CharField(blank=True, default="", max_length=64)),
                ("code_hash", models.CharField(blank=True, default="", max_length=128)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reviewed_password_reset_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="password_reset_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="passwordresetrequest",
            index=models.Index(fields=["status", "created_at"], name="acct_pwdreset_status_idx"),
        ),
        migrations.AddIndex(
            model_name="passwordresetrequest",
            index=models.Index(fields=["user", "created_at"], name="acct_pwdreset_user_idx"),
        ),
    ]
