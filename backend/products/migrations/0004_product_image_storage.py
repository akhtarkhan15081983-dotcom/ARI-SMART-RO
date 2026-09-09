from django.db import migrations, models
import products.storage


class Migration(migrations.Migration):
    dependencies = [("products", "0003_romodel_storefront_fields_and_images")]

    operations = [
        migrations.AlterField(
            model_name="romodelimage",
            name="image",
            field=models.ImageField(
                upload_to="products/ro_models/",
                storage=products.storage.product_image_storage,
            ),
        ),
    ]
