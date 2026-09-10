from django.db import migrations, models


def preserve_existing_availability(apps, schema_editor):
    ROModel = apps.get_model("products", "ROModel")
    for product in ROModel.objects.all().iterator():
        product.available_for_sale = product.business_type == "SALE" and product.selling_price > 0
        product.available_for_rent = product.business_type == "RENT" and product.monthly_rent > 0
        product.save(update_fields=["available_for_sale", "available_for_rent"])


class Migration(migrations.Migration):
    dependencies = [("products", "0004_product_image_storage")]

    operations = [
        migrations.AddField(
            model_name="romodel",
            name="available_for_sale",
            field=models.BooleanField(default=True, help_text="Show the Buy option when a valid selling price is configured."),
        ),
        migrations.AddField(
            model_name="romodel",
            name="available_for_rent",
            field=models.BooleanField(default=False, help_text="Show the Rent option when a valid monthly rent is configured."),
        ),
        migrations.RunPython(preserve_existing_availability, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="romodel",
            name="business_type",
            field=models.CharField(choices=[("RENT", "Rental"), ("SALE", "Sale"), ("AMC", "AMC")], help_text="Legacy primary type. Store visibility is controlled by the Sale and Rent options below.", max_length=10),
        ),
    ]
