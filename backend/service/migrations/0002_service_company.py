from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("service", "0001_initial"),
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="services",
                to="tenancy.company",
            ),
        ),
    ]
