from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("customers", "0017_rent_offer_audit")]
    operations = [
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="existing_customer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calling_leads", to="customers.customer"),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="priority",
            field=models.CharField(choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")], default="NORMAL", max_length=10),
        ),
        migrations.CreateModel(
            name="CallingActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("outcome", models.CharField(choices=[("PENDING", "Pending"), ("NO_ANSWER", "No Answer"), ("CALLBACK", "Call Back"), ("INTERESTED", "Interested"), ("NOT_INTERESTED", "Not Interested"), ("WRONG_NUMBER", "Wrong Number"), ("CONVERTED", "Converted")], max_length=20)),
                ("note", models.TextField(blank=True, default="")),
                ("next_follow_up_at", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("called_at", models.DateTimeField(auto_now_add=True)),
                ("caller", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calling_activities", to="employees.employeeprofile")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calling_activities", to="customers.customer")),
                ("lead", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="call_activities", to="customers.publiccustomerrequest")),
            ],
            options={"ordering": ["-called_at", "-id"]},
        ),
    ]
