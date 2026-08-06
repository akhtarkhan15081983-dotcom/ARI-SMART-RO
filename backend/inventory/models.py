from django.db import models
from partmaster.models import PartMaster
from purchase.models import PurchaseItem
from employees.models import EmployeeProfile
import os
import qrcode
from io import BytesIO
from django.core.files import File

class InventoryItem(models.Model):
    STATUS_CHOICES = [
        ("IN_STOCK", "In Stock"),
        ("ISSUED", "Issued To Engineer"),
        ("INSTALLED", "Installed"),
        ("RETURNED", "Returned"),
        ("SCRAP", "Scrap"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="IN_STOCK"
    )

    purchase_item = models.ForeignKey(
        PurchaseItem,
        on_delete=models.PROTECT,
        related_name="inventory_items"
    )

    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT
    )

    serial_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )
    barcode = models.CharField(
        max_length=100,
        blank=True
    )

    manufacturing_date = models.DateField(
        blank=True,
        null=True
    )

    expiry_date = models.DateField(
        blank=True,
        null=True
    )

    qr_code = models.ImageField(
        upload_to="qr_codes/",
        blank=True,
        null=True
    )

    

    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):

        is_new = self.pk is None

        super().save(*args, **kwargs)

        if self.serial_number and not self.qr_code:

            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=4,
            )

            qr.add_data(self.serial_number)
            qr.make(fit=True)

            img = qr.make_image(
                fill_color="black",
                back_color="white",
            )

            buffer = BytesIO()

            img.save(buffer, format="PNG")

            filename = f"{self.serial_number}.png"

            self.qr_code.save(
                filename,
                File(buffer),
                save=False,
            )

            super().save(update_fields=["qr_code"])

    def __str__(self):
        return self.serial_number or f"Inventory #{self.id}"

class EngineerBagItem(models.Model):

    STATUS_CHOICES = [
        ("ISSUED", "Issued"),
        ("INSTALLED", "Installed"),
        ("RETURNED", "Returned"),
    ]

    engineer = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="bag_items"
    )

    inventory_item = models.OneToOneField(
        "InventoryItem",
        on_delete=models.CASCADE,
        related_name="bag_item"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ISSUED"
    )

    issue_date = models.DateTimeField(auto_now_add=True)

    install_date = models.DateTimeField(
        blank=True,
        null=True
    )

    return_date = models.DateTimeField(
        blank=True,
        null=True
    )

    remarks = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"{self.engineer.employee_id} - {self.inventory_item.serial_number}"


