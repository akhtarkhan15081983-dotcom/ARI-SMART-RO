from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("employees", "0010_employeepenalty")]
    operations = [
        migrations.AlterField(
            model_name="employeeprofile",
            name="designation",
            field=models.CharField(
                choices=[
                    ("ENGINEER", "Engineer"),
                    ("MANAGER", "Manager"),
                    ("OFFICE", "Office Staff"),
                    ("CALLING", "Calling Staff"),
                ],
                max_length=20,
            ),
        ),
    ]
