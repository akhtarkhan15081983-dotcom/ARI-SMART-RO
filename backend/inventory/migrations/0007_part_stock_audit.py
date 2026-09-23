from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0006_inventoryitem_received_at_inventoryitem_received_by_and_more"),
        ("partmaster", "0003_partmaster_replacement_interval_days"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PartStockAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(blank=True, max_length=32, unique=True)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("COMPLETED", "Completed")], default="OPEN", max_length=15)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("started_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="started_part_stock_audits", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PartStockAuditLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_serialized", models.BooleanField(default=False)),
                ("expected_quantity", models.PositiveIntegerField(default=0)),
                ("counted_quantity", models.PositiveIntegerField(default=0)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("remarks", models.CharField(blank=True, default="", max_length=300)),
                ("audit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="inventory.partstockaudit")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_audit_lines", to="partmaster.partmaster")),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="verified_part_stock_audit_lines", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["part__name"], "unique_together": {("audit", "part")}},
        ),
        migrations.CreateModel(
            name="PartStockAuditScan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scanned_at", models.DateTimeField(auto_now_add=True)),
                ("audit_line", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scans", to="inventory.partstockauditline")),
                ("inventory_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="physical_audit_scans", to="inventory.inventoryitem")),
                ("scanned_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_stock_audit_scans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("audit_line", "inventory_item")}},
        ),
    ]
