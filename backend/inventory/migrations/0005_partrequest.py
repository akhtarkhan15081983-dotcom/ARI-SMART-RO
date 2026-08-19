from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_inventoryauditlog"),
        ("employees", "0001_initial"),
        ("partmaster", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PartRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("remarks", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("FULFILLED", "Fulfilled")], default="PENDING", max_length=20)),
                ("review_remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("engineer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="part_requests", to="employees.employeeprofile")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="engineer_requests", to="partmaster.partmaster")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_part_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
