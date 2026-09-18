from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customers", "0011_calling_desk")]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="ownership_type",
            field=models.CharField(
                choices=[("RENTAL", "Rental"), ("PURCHASE", "Purchased")],
                default="RENTAL",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="customer",
            name="rent_to_purchase_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="rent_to_purchase_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="customer",
            name="rent_at_conversion",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="customer",
            name="security_adjusted_at_conversion",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="customer",
            name="rent_to_purchase_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="customer",
            name="deactivated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="deactivation_reason",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
    ]
