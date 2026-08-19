from django.db import models
from django.utils import timezone

from products.models import ROModel
from customers.models import Customer


class ROAsset(models.Model):

    STATUS_CHOICES = [
        ("WAREHOUSE", "Warehouse"),
        ("ASSIGNED", "Assigned"),
        ("INSTALLED", "Installed"),
        ("SERVICE", "Service"),
        ("REPAIR", "Repair"),
        ("RETURNED", "Returned"),
        ("REFURBISHED", "Refurbished"),
        ("SCRAP", "Scrap"),
    ]

    asset_id = models.CharField(
        max_length=25,
        unique=True,
        blank=True
    )

    ro_model = models.ForeignKey(
        ROModel,
        on_delete=models.PROTECT,
        related_name="assets"
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True
    )

    qr_code = models.CharField(
        max_length=200,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="WAREHOUSE"
    )

    current_customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ro_assets"
    )

    purchase_date = models.DateField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if not self.asset_id:

            year = timezone.now().year

            last = ROAsset.objects.order_by("-id").first()

            if last:
                try:
                    last_no = int(last.asset_id.split("-")[-1])
                except Exception:
                    last_no = 0
            else:
                last_no = 0

            self.asset_id = f"ARI-RO-{year}-{last_no+1:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.asset_id