from django.db import models
from django.utils import timezone

from accounts.models import User


class Customer(models.Model):

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]

    customer_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
    )

    card_number = models.CharField(
        max_length=25,
        blank=True,
        default=""
    )

    old_card_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    name = models.CharField(max_length=150)

    phone = models.CharField(
        max_length=10,
        unique=True
    )

    alternate_phone = models.CharField(
        max_length=10,
        blank=True
    )

    email = models.EmailField(blank=True)

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True
    )

    address = models.TextField()

    area = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    pincode = models.CharField(
        max_length=10
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    ro_model = models.CharField(
        max_length=100
    )

    installation_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    installation_date = models.DateField(
        null=True,
        blank=True
    )

    assigned_engineer = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        if not self.customer_id:
            year = timezone.now().year

            last_customer = Customer.objects.order_by("-id").first()

            if last_customer:
                try:
                    last_number = int(last_customer.customer_id.split("-")[-1])
                except (ValueError, IndexError):
                    last_number = 0
            else:
                last_number = 0

            new_number = last_number + 1

            self.customer_id = f"CUS-{year}-{new_number:06d}"

            self.card_number = f"ARI-{year}-{new_number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class CustomerRentHistory(models.Model):

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="rent_history",
    )

    rent_month = models.DateField(
        null=True,
        blank=True,
    )

    expected_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    raw_value = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    remarks = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = [
            "rent_month",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "customer",
                    "rent_month",
                ],
                name="unique_customer_rent_month",
            )
        ]

    def __str__(self):

        return (
            f"{self.customer.name} - "
            f"{self.rent_month} - "
            f"{self.paid_amount}"
        )

class CustomerRentPayment(models.Model):

    PAYMENT_MODE_CHOICES = [
        ("CASH", "Cash"),
        ("UPI", "UPI"),
        ("BANK", "Bank Transfer"),
        ("OTHER", "Other"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="rent_payments",
    )

    rent_history = models.ForeignKey(
        CustomerRentHistory,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    payment_date = models.DateField(
        default=timezone.now,
    )

    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        default="CASH",
    )

    remarks = models.TextField(
        blank=True,
        default="",
    )

    collected_by = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collected_rent_payments",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.customer.name} - "
            f"₹{self.amount} - "
            f"{self.payment_date}"
        )


class CustomerLocationLog(models.Model):
    SOURCE_CHOICES = [
        ("WORK_CALENDAR", "Work Calendar"),
        ("WORK_ROUTE", "Work Route"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="location_logs",
    )
    captured_by = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_locations_captured",
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="WORK_CALENDAR")
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-captured_at"]

    def __str__(self):
        return f"{self.customer.customer_id} - {self.captured_at}"

