from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0020_customer_company"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="rent_due_day",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(31)],
                help_text=(
                    "Monthly RO rent due day (1-31). If blank, the installation "
                    "day is used for backward compatibility."
                ),
            ),
        ),
    ]
