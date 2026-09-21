from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0017_corporate_30_day_training"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="employeetrainingassignment",
            name="scheduled_start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="employeetrainingassignment",
            name="release_interval_days",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="employeetrainingassignment",
            name="lesson_completed_at",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="employeetrainingassignment",
            name="scheduled_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="scheduled_training_assignments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="employeetrainingassignment",
            name="schedule_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
