from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="attendance",
            name="identity_review_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending human review"),
                    ("APPROVED", "Approved by admin"),
                    ("REJECTED", "Rejected by admin"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="attendance",
            name="identity_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="attendance",
            name="identity_review_note",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="attendance",
            name="identity_reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="attendance_identity_reviews",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
