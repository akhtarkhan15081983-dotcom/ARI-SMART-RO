from django.db import migrations
from django.utils import timezone


def reset_faizan_device_binding(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    EmployeeProfile = apps.get_model('employees', 'EmployeeProfile')

    user = User.objects.filter(phone='8923908729').first()
    if user is None:
        return

    user.previous_login_device_id = user.active_login_device_id or ''
    user.active_login_device_id = ''
    user.login_device_bound_at = None
    user.login_device_reset_at = timezone.now()
    user.save(
        update_fields=[
            'previous_login_device_id',
            'active_login_device_id',
            'login_device_bound_at',
            'login_device_reset_at',
        ]
    )

    EmployeeProfile.objects.filter(user_id=user.id).update(attendance_device_id='')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0023_employee_location_point'),
    ]

    operations = [
        migrations.RunPython(reset_faizan_device_binding, noop_reverse),
    ]
