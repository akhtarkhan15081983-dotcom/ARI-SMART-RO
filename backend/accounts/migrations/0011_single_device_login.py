from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_notification_center_offer_engine"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="active_login_device_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="user",
            name="previous_login_device_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="user",
            name="login_device_bound_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="login_device_reset_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
