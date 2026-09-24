from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_single_device_login"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authsecurityevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("LOGIN_SUCCESS", "Login Success"),
                    ("LOGIN_FAILED", "Login Failed"),
                    ("LOGIN_DEVICE_BLOCKED", "Login Device Blocked"),
                    ("LOGIN_DEVICE_RESET", "Login Device Reset"),
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
    ]
