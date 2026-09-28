from uuid import uuid4
from django.db import migrations


def backfill(apps, schema_editor):
    InventoryItem = apps.get_model("inventory", "InventoryItem")
    rows = InventoryItem.objects.filter(
        status="PENDING_RECEIPT",
        serial_number__isnull=True,
        part__is_serialized=True,
    ).select_related("part")
    for row in rows.iterator():
        while True:
            code = f"ARI-{row.part.code}-{uuid4().hex[:10].upper()}"
            if not InventoryItem.objects.filter(serial_number=code).exists():
                break
        row.serial_number = code
        row.barcode = code
        row.save(update_fields=["serial_number", "barcode"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("inventory", "0007_inventoryitem_receipt_photo")]
    operations = [migrations.RunPython(backfill, reverse_noop)]
