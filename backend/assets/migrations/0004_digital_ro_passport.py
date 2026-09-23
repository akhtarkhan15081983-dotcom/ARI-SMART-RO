from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0003_roasset_workflow_fields_and_movement"),
        ("partmaster", "0002_partmaster_is_serialized"),
        ("inventory", "0006_inventoryitem_received_at_inventoryitem_received_by_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ROAssetComponent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("serial_number", models.CharField(blank=True, db_index=True, default="", max_length=100)),
                ("batch_number", models.CharField(blank=True, default="", max_length=100)),
                ("source", models.CharField(choices=[("FACTORY_BOM", "Factory / Model BOM"), ("INSTALLATION", "Installation"), ("SERVICE", "Service Replacement"), ("MANUAL", "Manual Correction")], default="FACTORY_BOM", max_length=20)),
                ("source_reference", models.CharField(blank=True, db_index=True, default="", max_length=80)),
                ("status", models.CharField(choices=[("ACTIVE", "Active / Installed"), ("REPLACED", "Replaced"), ("REMOVED", "Removed")], default="ACTIVE", max_length=20)),
                ("scan_status", models.CharField(choices=[("NOT_REQUIRED", "Scan not required"), ("PENDING", "Scan / serial verification pending"), ("VERIFIED", "Serial / QR verified")], default="NOT_REQUIRED", max_length=20)),
                ("installed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, default="", max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="components", to="assets.roasset")),
                ("installed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="installed_ro_components", to=settings.AUTH_USER_MODEL)),
                ("inventory_item", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ro_asset_component", to="inventory.inventoryitem")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ro_asset_components", to="partmaster.partmaster")),
            ],
            options={"ordering": ["part__name", "id"]},
        ),
        migrations.AddIndex(
            model_name="roassetcomponent",
            index=models.Index(fields=["asset", "status"], name="assets_roas_asset_i_73a829_idx"),
        ),
        migrations.AddIndex(
            model_name="roassetcomponent",
            index=models.Index(fields=["asset", "scan_status"], name="assets_roas_asset_i_9c1b12_idx"),
        ),
        migrations.CreateModel(
            name="ROAssetComponentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("CREATED", "Component created"), ("SCAN_VERIFIED", "Serial / QR verified"), ("INSTALLATION_VERIFIED", "Verified at installation"), ("REPLACED", "Component replaced"), ("REMOVED", "Component removed"), ("QUANTITY_CHANGED", "Quantity changed"), ("NOTE", "Note")], max_length=30)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("serial_number", models.CharField(blank=True, default="", max_length=100)),
                ("from_status", models.CharField(blank=True, default="", max_length=20)),
                ("to_status", models.CharField(blank=True, default="", max_length=20)),
                ("source_reference", models.CharField(blank=True, db_index=True, default="", max_length=80)),
                ("remarks", models.CharField(blank=True, default="", max_length=500)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ro_component_events", to=settings.AUTH_USER_MODEL)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="component_events", to="assets.roasset")),
                ("component", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="assets.roassetcomponent")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ro_component_events", to="partmaster.partmaster")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
