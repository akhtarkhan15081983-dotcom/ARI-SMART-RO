from django.db import models
from partmaster.models import PartMaster


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100,blank=True)
    state = models.CharField(max_length=100,blank=True)
    pincode = models.CharField(max_length=10,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name




class Purchase(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchases"
    )

    invoice_number = models.CharField(max_length=50)
    invoice_date = models.DateField()

    remarks = models.TextField(blank=True)

    invoice_image = models.ImageField(upload_to="purchase_invoices/%Y/%m/", blank=True, null=True)
    entry_source = models.CharField(
        max_length=20,
        choices=(("MANUAL", "Manual"), ("INVOICE_OCR", "Invoice OCR")),
        default="MANUAL",
    )
    ocr_text = models.TextField(blank=True)
    ocr_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    verified_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verified_purchases",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.name}"


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items"
    )

    part = models.ForeignKey(
        PartMaster,
        on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField()

    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.part.name} ({self.quantity})"
