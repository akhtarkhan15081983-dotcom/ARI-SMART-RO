from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_notification_center_offer_engine"),
        ("customers", "0016_remove_old_992_customers"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerrenthistory",
            name="base_rent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="customerrenthistory",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="customerrenthistory",
            name="applied_offer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rent_history_applications", to="accounts.customerengagement"),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="base_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="discount_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="applied_offer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="public_request_applications", to="accounts.customerengagement"),
        ),
    ]
