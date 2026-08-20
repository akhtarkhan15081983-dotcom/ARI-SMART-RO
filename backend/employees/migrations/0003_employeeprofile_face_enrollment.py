from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0002_employeeprofile_is_online_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="employeeprofile",
            name="face_enrolled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeeprofile",
            name="face_enrollment_verified",
            field=models.BooleanField(default=False),
        ),
    ]
