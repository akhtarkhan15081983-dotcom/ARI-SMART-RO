from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0010_alter_customerlocationlog_source"),
        ("employees", "0011_add_calling_designation"),
    ]
    operations = [
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="assigned_caller",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="calling_requests",
                to="employees.employeeprofile",
            ),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="last_call_outcome",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("NO_ANSWER", "No Answer"),
                    ("CALLBACK", "Call Back"),
                    ("INTERESTED", "Interested"),
                    ("NOT_INTERESTED", "Not Interested"),
                    ("WRONG_NUMBER", "Wrong Number"),
                    ("CONVERTED", "Converted"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="next_follow_up_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="last_called_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="call_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="publiccustomerrequest",
            name="call_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
