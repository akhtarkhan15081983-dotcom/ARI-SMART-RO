from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0013_clientactionreceipt"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="ro_asset",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="jobs",
                to="assets.roasset",
            ),
        ),
    ]
