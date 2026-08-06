from django.db import models
from django.utils import timezone


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

    card_number = models.CharField(
        max_length=25,
        blank=True,
        default=""
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