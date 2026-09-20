from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_add_calling_role"),
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
                ],
                max_length=24,
            ),
        ),
    ]
