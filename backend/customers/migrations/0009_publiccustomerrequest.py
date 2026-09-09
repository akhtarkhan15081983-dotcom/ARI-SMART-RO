import customers.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0008_customerlocationlog"),
        ("products", "0004_product_image_storage"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicCustomerRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_number", models.CharField(default=customers.models.public_request_number, editable=False, max_length=25, unique=True)),
                ("request_type", models.CharField(choices=[("PURCHASE", "Product Purchase"), ("RENTAL", "Product Rental"), ("SERVICE", "RO Service"), ("AMC", "AMC Plan"), ("COMPLAINT", "Complaint"), ("REFERRAL", "Referral Enquiry")], max_length=15)),
                ("plan_name", models.CharField(blank=True, max_length=150)),
                ("customer_name", models.CharField(max_length=150)),
                ("phone", models.CharField(db_index=True, max_length=10)),
                ("alternate_phone", models.CharField(blank=True, max_length=10)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("address", models.TextField()),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("pincode", models.CharField(max_length=6)),
                ("quantity", models.PositiveSmallIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("payment_method", models.CharField(choices=[("COD", "Cash/UPI on Delivery"), ("OFFICE", "Confirm with ARI Team")], default="OFFICE", max_length=10)),
                ("preferred_date", models.DateField(blank=True, null=True)),
                ("referral_code", models.CharField(blank=True, max_length=30)),
                ("notes", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("NEW", "New"), ("CONTACTED", "Customer Contacted"), ("CONFIRMED", "Confirmed"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")], default="NEW", max_length=15)),
                ("source", models.CharField(default="MOBILE_GUEST", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="public_requests", to="products.romodel")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
