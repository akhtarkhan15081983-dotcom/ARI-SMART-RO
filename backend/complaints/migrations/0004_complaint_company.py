from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0003_repair_assigned_complaint_status"),
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="complaint",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="complaints",
                to="tenancy.company",
            ),
        ),
    ]
