from django.db import migrations, models
import django.db.models.deletion


def preserve_existing_courses(apps, schema_editor):
    Course = apps.get_model("employees", "TrainingCourse")
    Company = apps.get_model("tenancy", "Company")
    ari = Company.objects.filter(slug="ari-smart-ro").first()
    for course in Course.objects.all():
        updates = []
        if not course.is_published:
            course.is_published = True
            updates.append("is_published")
        if ari is not None and course.company_id is None:
            course.company_id = ari.id
            updates.append("company")
        # Existing corporate course historically required trainer review on
        # every lesson before certificate issue.
        lesson_count = course.lessons.count()
        if lesson_count and course.required_trainer_reviews == 0:
            course.required_trainer_reviews = lesson_count
            updates.append("required_trainer_reviews")
        if updates:
            course.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0018_training_certificate"),
        ("tenancy", "0006_role_feature_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainingcourse",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="training_courses",
                to="tenancy.company",
            ),
        ),
        migrations.AddField(
            model_name="trainingcourse",
            name="is_published",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="trainingcourse",
            name="certificate_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="trainingcourse",
            name="certificate_valid_days",
            field=models.PositiveIntegerField(default=365),
        ),
        migrations.AddField(
            model_name="trainingcourse",
            name="required_trainer_reviews",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="trainingcourse",
            name="minimum_trainer_average",
            field=models.DecimalField(decimal_places=2, default=3.0, max_digits=3),
        ),
        migrations.AddField(
            model_name="traininglesson",
            name="video_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="traininglesson",
            name="resource_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="traininglesson",
            name="resource_label",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.RunPython(preserve_existing_courses, migrations.RunPython.noop),
    ]
