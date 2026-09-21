from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0017_corporate_30_day_training"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TrainingCertificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("certificate_number", models.CharField(max_length=40, unique=True)),
                ("verification_code", models.CharField(max_length=48, unique=True)),
                ("quiz_score", models.PositiveIntegerField(default=0)),
                ("trainer_average", models.DecimalField(decimal_places=2, default=0, max_digits=4)),
                ("final_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
                ("valid_until", models.DateField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revoke_reason", models.CharField(blank=True, default="", max_length=500)),
                ("assignment", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="certificate", to="employees.employeetrainingassignment")),
                ("issued_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="training_certificates_issued", to=settings.AUTH_USER_MODEL)),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="training_certificates_revoked", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-issued_at"]},
        ),
    ]
