from django.db import models

# Create your models here.
from django.db import models


class PartCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Part Category"
        verbose_name_plural = "Part Categories"

    def __str__(self):
        return self.name


class PartMaster(models.Model):
    UNIT_CHOICES = [
        ("PCS", "Piece"),
        ("SET", "Set"),
        ("MTR", "Meter"),
        ("LTR", "Liter"),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(
        PartCategory,
        on_delete=models.PROTECT,
        related_name="parts"
    )
    brand = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="PCS")
    is_serialized = models.BooleanField(
        default=False,
        help_text="Enable for parts that require serial number tracking."
    )
    warranty_months = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Part"
        verbose_name_plural = "Parts"

    def __str__(self):
        return f"{self.code} - {self.name}"