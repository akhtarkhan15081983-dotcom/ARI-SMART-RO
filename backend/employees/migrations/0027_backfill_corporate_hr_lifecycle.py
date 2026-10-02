from calendar import monthrange

from django.db import migrations


def _add_months(value, months):
    total = value.year * 12 + (value.month - 1) + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def backfill_hr_lifecycle(apps, schema_editor):
    EmployeeProfile = apps.get_model("employees", "EmployeeProfile")
    EmployeeHrLifecycle = apps.get_model("employees", "EmployeeHrLifecycle")

    for employee in EmployeeProfile.objects.all().iterator(chunk_size=500):
        start = employee.joining_date
        if start is None:
            continue
        EmployeeHrLifecycle.objects.get_or_create(
            employee_id=employee.id,
            defaults={
                "employment_type": "PROBATION",
                "employment_status": "ONBOARDING" if employee.is_active else "INACTIVE",
                "hr_stage": "CREATED",
                "probation_months": 3,
                "probation_start_date": start,
                "confirmation_due_date": _add_months(start, 3),
            },
        )


def noop_reverse(apps, schema_editor):
    # Historical lifecycle rows are intentionally preserved on rollback.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0026_corporate_hr_lifecycle"),
    ]

    operations = [
        migrations.RunPython(backfill_hr_lifecycle, noop_reverse),
    ]
