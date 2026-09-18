from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_customer_engagement")]
    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Admin"),
                    ("MANAGER", "Manager"),
                    ("ENGINEER", "Engineer"),
                    ("OFFICE", "Office Staff"),
                    ("CALLING", "Calling Staff"),
                    ("CUSTOMER", "Customer"),
                ],
                default="ENGINEER",
                max_length=20,
            ),
        ),
    ]
