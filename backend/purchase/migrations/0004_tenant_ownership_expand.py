from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("purchase", "0003_purchase_entry_source_purchase_invoice_image_and_more"),
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="suppliers",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="purchase",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="purchases",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="purchaseitem",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="purchase_items",
                to="tenancy.company",
            ),
        ),
    ]
