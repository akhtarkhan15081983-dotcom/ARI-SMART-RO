from django.db import migrations


def repair_assigned_complaint_status(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    Complaint.objects.filter(
        status="NEW",
        engineer__isnull=False,
    ).update(status="ASSIGNED")


class Migration(migrations.Migration):
    dependencies = [
        ("complaints", "0002_complaint_job"),
    ]

    operations = [
        migrations.RunPython(
            repair_assigned_complaint_status,
            migrations.RunPython.noop,
        ),
    ]
