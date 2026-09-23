from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("partmaster", "0002_partmaster_is_serialized")]

    operations = [
        migrations.AddField(
            model_name="partmaster",
            name="replacement_interval_days",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Recommended replacement interval in days. Use 0 when the part has no scheduled replacement cycle.",
            ),
        ),
    ]
