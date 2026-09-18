from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customers", "0013_import_latest_missing_customers")]

    operations = [
        migrations.AlterField(
            model_name="customer",
            name="phone",
            field=models.CharField(blank=True, db_index=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="customer",
            name="import_batch",
            field=models.CharField(blank=True, db_index=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_source_sheet",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_source_row",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_raw_phone",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_employee",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_reference",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_installer",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_remarks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_mh",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="customer",
            name="legacy_excel_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
