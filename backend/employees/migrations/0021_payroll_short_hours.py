from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0020_expand_corporate_training_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="payrollrecord",
            name="short_hours",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name="payrollrecord",
            name="short_hours_deduction",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
