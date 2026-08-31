from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("referrals", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="referral",
            name="claim_fingerprint",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="referral",
            name="risk_reasons",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="referral",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("QUALIFIED", "Qualified"),
                    ("REJECTED", "Rejected"),
                    ("REVERSED", "Reversed"),
                    ("REVIEW", "Review Required"),
                ],
                default="PENDING",
                max_length=12,
            ),
        ),
    ]
