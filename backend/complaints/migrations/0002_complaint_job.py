from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0001_initial"),
        ("jobs", "0013_clientactionreceipt"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="job",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="complaint_source",
                to="jobs.job",
            ),
        ),
    ]
