from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0004_employeeprofile_attendance_device_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="face_enrollment_allowed",
            field=models.BooleanField(default=False),
        ),
    ]
