from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="HumanReadableIdSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("namespace", models.CharField(max_length=40)),
                ("year", models.PositiveSmallIntegerField()),
                ("next_value", models.PositiveBigIntegerField(default=1)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["namespace", "year"]},
        ),
        migrations.AddConstraint(
            model_name="humanreadableidsequence",
            constraint=models.UniqueConstraint(
                fields=("namespace", "year"),
                name="unique_human_readable_id_sequence",
            ),
        ),
    ]
