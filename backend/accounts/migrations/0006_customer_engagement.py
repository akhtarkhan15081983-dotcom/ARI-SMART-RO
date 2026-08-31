from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_simverificationchallenge_pending_password_hash")]

    operations = [
        migrations.CreateModel(
            name="CustomerEngagement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("OFFER", "Offer"), ("PAYMENT", "Payment Alert"), ("SERVICE", "Service Reminder"), ("ANNOUNCEMENT", "Announcement")], default="ANNOUNCEMENT", max_length=16)),
                ("audience", models.CharField(choices=[("ALL", "All Customers"), ("TARGETED", "Targeted Customer")], default="ALL", max_length=12)),
                ("title", models.CharField(max_length=120)),
                ("message", models.TextField(max_length=500)),
                ("badge_text", models.CharField(blank=True, default="", max_length=30)),
                ("discount_type", models.CharField(choices=[("NONE", "No Discount"), ("PERCENT", "Percentage"), ("FIXED", "Fixed Amount")], default="NONE", max_length=10)),
                ("discount_value", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("promo_code", models.CharField(blank=True, default="", max_length=30)),
                ("terms", models.CharField(blank=True, default="", max_length=300)),
                ("valid_from", models.DateTimeField(default=django.utils.timezone.now)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("priority", models.PositiveSmallIntegerField(default=50)),
                ("action", models.CharField(choices=[("NONE", "No Action"), ("SHOP", "Open Shop"), ("RENT", "Pay Rent"), ("SERVICE", "Book Service"), ("REFERRAL", "Open Referral")], default="NONE", max_length=12)),
                ("action_label", models.CharField(blank=True, default="", max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_engagements", to=settings.AUTH_USER_MODEL)),
                ("target_user", models.ForeignKey(blank=True, limit_choices_to={"role": "CUSTOMER"}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="targeted_engagements", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-priority", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CustomerEngagementRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("read_at", models.DateTimeField(auto_now_add=True)),
                ("engagement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="read_receipts", to="accounts.customerengagement")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="engagement_reads", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="customerengagementread",
            constraint=models.UniqueConstraint(fields=("engagement", "user"), name="unique_engagement_read"),
        ),
    ]
