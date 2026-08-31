from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("referrals", "0002_referral_fraud_review")]

    operations = [
        migrations.AlterField(
            model_name="walletreward",
            name="reward_type",
            field=models.CharField(
                choices=[
                    ("APP_WELCOME", "App Welcome Reward"),
                    ("APP_REFERRAL_POINTS", "App Referral — 100 Points"),
                    ("RENT_REFERRAL", "Rent to Rent Referral"),
                    ("RENT_TO_PURCHASE", "Rent to Purchase Referral"),
                    ("PURCHASE_TO_RENT", "Purchase to Rent Referral"),
                    ("PURCHASE_REFERRAL", "Purchase to Purchase Referral"),
                ],
                max_length=30,
            ),
        ),
    ]
