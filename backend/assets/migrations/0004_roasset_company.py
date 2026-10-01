from django.db import migrations, models
import django.db.models.deletion


def backfill_asset_company(apps, schema_editor):
    ROAsset = apps.get_model("assets", "ROAsset")
    for asset in ROAsset.objects.select_related("current_customer").filter(
        company__isnull=True,
        current_customer__isnull=False,
    ).iterator():
        company_id = getattr(asset.current_customer, "company_id", None)
        if company_id:
            ROAsset.objects.filter(pk=asset.pk, company__isnull=True).update(
                company_id=company_id
            )


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0003_ro_alarm_center"),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="roasset",
            name="company",
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ro_assets",
                to="tenancy.company",
            ),
        ),
        migrations.RunPython(
            backfill_asset_company,
            migrations.RunPython.noop,
        ),
    ]
