from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0008_backfill_serialized_pending_codes"),
        ("purchase", "0004_tenant_ownership_expand"),
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="inventoryitem",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inventory_items",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="engineerbagitem",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="engineer_bag_items",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="inventoryauditlog",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inventory_audit_logs",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="partrequest",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="part_requests",
                to="tenancy.company",
            ),
        ),
    ]
