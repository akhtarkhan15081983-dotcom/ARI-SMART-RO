from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0006_inventoryitem_received_at_inventoryitem_received_by_and_more")]
    operations = [
        migrations.AddField(
            model_name="inventoryitem",
            name="receipt_photo",
            field=models.ImageField(blank=True, null=True, upload_to="inventory_receipts/%Y/%m/"),
        ),
    ]
