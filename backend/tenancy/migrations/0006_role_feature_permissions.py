from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0005_company_archived_at_company_deletion_scheduled_for_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RoleFeaturePermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(
                    choices=[
                        ("MANAGER", "Manager"),
                        ("OFFICE", "Office"),
                        ("CALLING", "Calling"),
                        ("ENGINEER", "Engineer"),
                    ],
                    max_length=12,
                )),
                ("feature_key", models.SlugField(max_length=80)),
                ("is_allowed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="role_feature_permissions",
                    to="tenancy.company",
                )),
                ("updated_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="role_permission_changes",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["role", "feature_key"]},
        ),
        migrations.AddConstraint(
            model_name="rolefeaturepermission",
            constraint=models.UniqueConstraint(
                fields=("company", "role", "feature_key"),
                name="unique_company_role_feature_permission",
            ),
        ),
    ]
