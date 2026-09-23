from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0002_alter_roasset_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="roasset",
            name="assigned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roasset",
            name="deployment_type",
            field=models.CharField(
                blank=True,
                choices=[("", "Unassigned"), ("SALE", "Sale"), ("RENT", "Rental")],
                default="",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="roasset",
            name="purchase_invoice",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="roasset",
            name="purchase_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.CreateModel(
            name="ROAssetMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("RECEIVED", "Received into warehouse"), ("SALE_ALLOCATED", "Allocated for sale"), ("RENT_ALLOCATED", "Allocated for rental"), ("INSTALLED", "Installed"), ("RENT_RETURNED", "Rental returned"), ("RESTOCKED", "Returned to warehouse"), ("REPAIR", "Sent to repair"), ("SCRAP", "Scrapped"), ("STATUS_CHANGE", "Status changed")], max_length=30)),
                ("request_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("request_number", models.CharField(blank=True, default="", max_length=30)),
                ("from_status", models.CharField(blank=True, default="", max_length=20)),
                ("to_status", models.CharField(blank=True, default="", max_length=20)),
                ("remarks", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movements", to="assets.roasset")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ro_asset_movements", to="customers.customer")),
                ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ro_asset_movements", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
