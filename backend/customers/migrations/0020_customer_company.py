from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0019_reassign_pushpendra_and_deactivate_rama"),
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="customers",
                to="tenancy.company",
            ),
        ),
    ]
