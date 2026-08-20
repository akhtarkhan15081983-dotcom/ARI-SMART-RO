from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0003_employeeprofile_face_enrollment"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="attendance_device_id",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]
