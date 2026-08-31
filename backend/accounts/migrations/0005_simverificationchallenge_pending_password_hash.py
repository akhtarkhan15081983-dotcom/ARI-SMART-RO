from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_sim_sms_gateway")]
    operations = [
        migrations.AddField(
            model_name="simverificationchallenge",
            name="pending_password_hash",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]
