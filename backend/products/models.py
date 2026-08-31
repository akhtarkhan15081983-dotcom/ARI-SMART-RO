from django.db import models
from partmaster.models import PartMaster


class ProductCategory(models.Model):

    name = models.CharField(max_length=100, unique=True)

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ROModel(models.Model):

    BUSINESS_TYPES = [
        ("RENT", "Rental"),
        ("SALE", "Sale"),
        ("AMC", "AMC"),
    ]

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="models"
    )

    model_name = models.CharField(max_length=150)

    capacity = models.CharField(
        max_length=50,
        help_text="Example: 12 LPH, 25 LPH, 50 LPH"
    )

    business_type = models.CharField(
        max_length=10,
        choices=BUSINESS_TYPES
    )

    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    installation_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    mrp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Maximum retail price shown before discount.",
    )

    stock_quantity = models.PositiveIntegerField(default=0)

    description = models.TextField(blank=True)

    features = models.TextField(
        blank=True,
        help_text="Enter one customer-facing feature per line.",
    )

    warranty_months = models.PositiveIntegerField(default=12)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.model_name


class ROModelImage(models.Model):
    ro_model = models.ForeignKey(
        ROModel,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/ro_models/")
    alt_text = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.ro_model.model_name} image {self.sort_order + 1}"





class ROModelPart(models.Model):

    ro_model = models.ForeignKey(
        ROModel,
        on_delete=models.CASCADE,
        related_name="standard_parts"
    )

    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField(default=1)

    is_mandatory = models.BooleanField(default=True)

    remarks = models.CharField(
        max_length=200,
        blank=True
    )

    class Meta:
        unique_together = ("ro_model", "part")

    def __str__(self):
        return f"{self.ro_model.model_name} - {self.part.name}"
