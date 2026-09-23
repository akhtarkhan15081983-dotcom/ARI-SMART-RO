from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("assets", "0004_digital_ro_passport"),
        ("customers", "0018_professional_calling_desk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="roasset",
            name="qc_status",
            field=models.CharField(
                choices=[("PENDING", "QC Pending"), ("PASSED", "QC Passed"), ("FAILED", "QC Failed")],
                default="PENDING",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="roasset",
            name="qc_checked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roasset",
            name="qc_checked_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="qc_checked_ro_assets",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="roasset",
            name="qc_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="roasset",
            name="cleaned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roasset",
            name="sanitized_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roasset",
            name="reserved_for_customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reserved_ro_assets",
                to="customers.customer",
            ),
        ),
        migrations.AddField(
            model_name="roasset",
            name="reserved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="roasset",
            name="reservation_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="roassetmovement",
            name="action",
            field=models.CharField(
                choices=[
                    ("RECEIVED", "Received into warehouse"),
                    ("QC_PASSED", "QC Passed"),
                    ("QC_FAILED", "QC Failed"),
                    ("RESERVED", "Reserved"),
                    ("RESERVATION_RELEASED", "Reservation Released"),
                    ("SALE_ALLOCATED", "Allocated for sale"),
                    ("RENT_ALLOCATED", "Allocated for rental"),
                    ("INSTALLED", "Installed"),
                    ("RENT_RETURNED", "Rental returned"),
                    ("RESTOCKED", "Returned to warehouse"),
                    ("REPAIR", "Sent to repair"),
                    ("SCRAP", "Scrapped"),
                    ("STATUS_CHANGE", "Status changed"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="ROStockAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(blank=True, max_length=30, unique=True)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("COMPLETED", "Completed")], default="OPEN", max_length=15)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("started_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="started_ro_stock_audits", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ROStockAuditItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expected_status", models.CharField(max_length=20)),
                ("physically_found", models.BooleanField(default=False)),
                ("scanned_at", models.DateTimeField(blank=True, null=True)),
                ("remarks", models.CharField(blank=True, default="", max_length=300)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_audit_items", to="assets.roasset")),
                ("audit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="assets.rostockaudit")),
                ("scanned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="scanned_ro_stock_audit_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("audit", "asset")}},
        ),
    ]
