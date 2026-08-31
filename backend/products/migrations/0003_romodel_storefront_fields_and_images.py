import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("products", "0002_romodelpart")]

    operations = [
        migrations.AddField(model_name="romodel", name="description", field=models.TextField(blank=True)),
        migrations.AddField(model_name="romodel", name="features", field=models.TextField(blank=True, help_text="Enter one customer-facing feature per line.")),
        migrations.AddField(model_name="romodel", name="mrp", field=models.DecimalField(decimal_places=2, default=0, help_text="Maximum retail price shown before discount.", max_digits=10)),
        migrations.AddField(model_name="romodel", name="stock_quantity", field=models.PositiveIntegerField(default=0)),
        migrations.CreateModel(
            name="ROModelImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="products/ro_models/")),
                ("alt_text", models.CharField(blank=True, max_length=160)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("ro_model", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="products.romodel")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
    ]
