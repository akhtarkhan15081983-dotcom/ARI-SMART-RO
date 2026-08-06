from django.db import models
from django.conf import settings
from django.utils import timezone



class EmployeeProfile(models.Model):

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]

    DESIGNATION_CHOICES = [
        ("ENGINEER", "Engineer"),
        ("MANAGER", "Manager"),
        ("OFFICE", "Office Staff"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile"
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True
    )

    photo = models.ImageField(
        upload_to="employees/",
        blank=True,
        null=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    aadhaar_number = models.CharField(
        max_length=12,
        blank=True
    )

    pan_number = models.CharField(
        max_length=10,
        blank=True
    )

    address = models.TextField(blank=True)

    city = models.CharField(max_length=100, blank=True)

    state = models.CharField(max_length=100, blank=True)

    pincode = models.CharField(max_length=10, blank=True)

    joining_date = models.DateField()

    designation = models.CharField(
        max_length=20,
        choices=DESIGNATION_CHOICES
    )

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    emergency_contact = models.CharField(
        max_length=10,
        blank=True
    )

    emergency_name = models.CharField(
        max_length=100,
        blank=True
    )

    # ===========================
    # Live Engineer Tracking
    # ===========================

    last_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    last_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    last_location_updated = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_online = models.BooleanField(
        default=False,
    )



    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):

        if not self.employee_id:
            year = timezone.now().year

            last_employee = EmployeeProfile.objects.order_by("-id").first()

            if last_employee:
                try:
                    last_number = int(last_employee.employee_id.split("-")[-1])
                except (ValueError, IndexError):
                    last_number = 0
            else:
                last_number = 0

            new_number = last_number + 1

            self.employee_id = f"EMP-{year}-{new_number:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


