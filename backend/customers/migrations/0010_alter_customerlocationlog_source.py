from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customers", "0009_publiccustomerrequest")]

    operations = [
        migrations.AlterField(
            model_name="customerlocationlog",
            name="source",
            field=models.CharField(
                choices=[
                    ("WORK_CALENDAR", "Work Calendar"),
                    ("WORK_ROUTE", "Work Route"),
                    ("RENT_COLLECTION", "Rent Collection"),
                ],
                default="WORK_CALENDAR",
                max_length=20,
            ),
        ),
    ]