from datetime import timedelta
import secrets

from django.db import migrations, models
from django.utils import timezone


def seed_employee_identity(apps, schema_editor):
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")
    now = timezone.now()
    localdate = timezone.localdate()

    for employee in EmployeeProfile.objects.all().iterator():
        changed = []
        if not employee.public_verification_code:
            while True:
                candidate = secrets.token_hex(6).upper()
                if not EmployeeProfile.objects.filter(public_verification_code=candidate).exists():
                    employee.public_verification_code = candidate
                    changed.append("public_verification_code")
                    break
        if employee.is_active:
            employee.onboarding_status = "READY"
            changed.append("onboarding_status")
        if employee.id_card_issued_at is None:
            employee.id_card_issued_at = now
            changed.append("id_card_issued_at")
        if employee.id_card_valid_until is None:
            employee.id_card_valid_until = localdate + timedelta(days=365 * 3)
            changed.append("id_card_valid_until")
        if changed:
            employee.save(update_fields=list(dict.fromkeys(changed)))


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0014_training_compliance"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="public_verification_code",
            field=models.CharField(blank=True, default="", max_length=24, unique=True),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="onboarding_status",
            field=models.CharField(
                choices=[
                    ("CREATED", "Created"),
                    ("PROFILE_PENDING", "Profile Pending"),
                    ("SECURITY_PENDING", "Security Pending"),
                    ("TRAINING_PENDING", "Training Pending"),
                    ("READY", "Ready"),
                ],
                default="CREATED",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="id_card_valid_until",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="id_card_issued_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(seed_employee_identity, migrations.RunPython.noop),
    ]
