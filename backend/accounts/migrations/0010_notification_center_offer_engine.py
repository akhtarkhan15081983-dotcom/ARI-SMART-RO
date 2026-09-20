from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_password_reset_requests"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="customerengagement",
            name="offer_scope",
            field=models.CharField(
                choices=[
                    ("NONE", "Message Only"), ("RENT", "Rent"), ("PURCHASE", "Purchase"),
                    ("SERVICE", "Service"), ("AMC", "AMC"), ("REFERRAL", "Referral"),
                ],
                default="NONE", max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="customerengagement",
            name="auto_apply",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customerengagement",
            name="max_discount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="customerengagement",
            name="minimum_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="customerengagement",
            name="action",
            field=models.CharField(
                choices=[
                    ("NONE", "No Action"), ("SHOP", "Open Shop"), ("RENT", "Pay Rent"),
                    ("SERVICE", "Book Service"), ("REFERRAL", "Open Referral"),
                    ("NOTIFICATIONS", "Open Notification Center"),
                ],
                default="NONE", max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="NotificationCampaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("message", models.TextField(max_length=1000)),
                ("category", models.CharField(
                    choices=[
                        ("GENERAL", "General"), ("HRMS", "HRMS"), ("ATTENDANCE", "Attendance"),
                        ("LEAVE", "Leave"), ("PAYROLL", "Payroll"), ("JOB", "Job"),
                        ("SERVICE", "Service"), ("COMPLAINT", "Complaint"), ("RENT", "Rent"),
                        ("PAYMENT", "Payment"), ("OFFER", "Offer"), ("SECURITY", "Security"),
                        ("SYSTEM", "System"),
                    ],
                    default="GENERAL", max_length=20,
                )),
                ("priority", models.CharField(
                    choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("CRITICAL", "Critical")],
                    default="NORMAL", max_length=10,
                )),
                ("audience", models.CharField(
                    choices=[
                        ("ALL", "Everyone"), ("CUSTOMERS", "All Customers"),
                        ("EMPLOYEES", "All Employees"), ("ROLE", "Specific Role"),
                        ("USERS", "Selected Users"),
                    ],
                    default="ALL", max_length=16,
                )),
                ("target_role", models.CharField(blank=True, choices=[
                    ("ADMIN", "Admin"), ("MANAGER", "Manager"), ("ENGINEER", "Engineer"),
                    ("OFFICE", "Office Staff"), ("CALLING", "Calling Staff"), ("CUSTOMER", "Customer"),
                ], default="", max_length=20)),
                ("action", models.CharField(
                    choices=[
                        ("NONE", "No Action"), ("SHOP", "Open Shop"), ("RENT", "Pay Rent"),
                        ("SERVICE", "Book Service"), ("REFERRAL", "Open Referral"),
                        ("NOTIFICATIONS", "Open Notification Center"),
                    ],
                    default="NONE", max_length=16,
                )),
                ("action_label", models.CharField(blank=True, default="", max_length=50)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_notification_campaigns", to=settings.AUTH_USER_MODEL)),
                ("target_users", models.ManyToManyField(blank=True, related_name="notification_campaign_targets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UserNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_key", models.CharField(blank=True, default="", max_length=160)),
                ("title", models.CharField(max_length=140)),
                ("message", models.TextField(max_length=1000)),
                ("category", models.CharField(
                    choices=[
                        ("GENERAL", "General"), ("HRMS", "HRMS"), ("ATTENDANCE", "Attendance"),
                        ("LEAVE", "Leave"), ("PAYROLL", "Payroll"), ("JOB", "Job"),
                        ("SERVICE", "Service"), ("COMPLAINT", "Complaint"), ("RENT", "Rent"),
                        ("PAYMENT", "Payment"), ("OFFER", "Offer"), ("SECURITY", "Security"),
                        ("SYSTEM", "System"),
                    ],
                    default="GENERAL", max_length=20,
                )),
                ("priority", models.CharField(choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("CRITICAL", "Critical")], default="NORMAL", max_length=10)),
                ("action", models.CharField(choices=[
                    ("NONE", "No Action"), ("SHOP", "Open Shop"), ("RENT", "Pay Rent"),
                    ("SERVICE", "Book Service"), ("REFERRAL", "Open Referral"),
                    ("NOTIFICATIONS", "Open Notification Center"),
                ], default="NONE", max_length=16)),
                ("action_label", models.CharField(blank=True, default="", max_length=50)),
                ("is_read", models.BooleanField(default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deliveries", to="accounts.notificationcampaign")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OfferRedemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_phone", models.CharField(blank=True, default="", max_length=15)),
                ("scope", models.CharField(choices=[
                    ("NONE", "Message Only"), ("RENT", "Rent"), ("PURCHASE", "Purchase"),
                    ("SERVICE", "Service"), ("AMC", "AMC"), ("REFERRAL", "Referral"),
                ], max_length=12)),
                ("reference", models.CharField(max_length=80)),
                ("base_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("discount_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("final_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("redeemed_at", models.DateTimeField(auto_now_add=True)),
                ("engagement", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="redemptions", to="accounts.customerengagement")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="offer_redemptions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-redeemed_at"]},
        ),
        migrations.AddIndex(
            model_name="usernotification",
            index=models.Index(fields=["user", "is_read", "created_at"], name="acct_notif_user_read_idx"),
        ),
        migrations.AddIndex(
            model_name="usernotification",
            index=models.Index(fields=["category", "created_at"], name="acct_notif_category_idx"),
        ),
        migrations.AddConstraint(
            model_name="usernotification",
            constraint=models.UniqueConstraint(fields=("user", "event_key"), name="unique_user_notification_event"),
        ),
        migrations.AddConstraint(
            model_name="offerredemption",
            constraint=models.UniqueConstraint(fields=("engagement", "scope", "reference"), name="unique_offer_scope_reference_redemption"),
        ),
    ]
