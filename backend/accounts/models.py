from django.db import models
from django.contrib.auth.models import AbstractUser

from .managers import UserManager


class User(AbstractUser):

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("MANAGER", "Manager"),
        ("ENGINEER", "Engineer"),
        ("OFFICE", "Office Staff"),
        ("CUSTOMER", "Customer"),
    ]

    username = None

    first_name = models.CharField(
        max_length=100
    )

    last_name = models.CharField(
        max_length=100,
        blank=True
    )

    email = models.EmailField(
        blank=True
    )

    phone = models.CharField(
        max_length=10,
        unique=True,
        db_index=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="ENGINEER"
    )

    is_verified = models.BooleanField(
        default=False
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"

    REQUIRED_FIELDS = []

    def __str__(self):
        return (
            f"{self.first_name} "
            f"({self.phone})"
        )


class PhoneOTP(models.Model):

    MAX_ATTEMPTS = 5

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="phone_otps",
    )

    otp = models.CharField(
        max_length=6
    )

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(
        default=0
    )

    is_used = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

    def __str__(self):
        return (
            f"{self.user.phone} - "
            f"{self.created_at}"
        )