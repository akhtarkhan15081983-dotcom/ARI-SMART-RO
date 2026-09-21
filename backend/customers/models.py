from django.db import models
from django.utils import timezone
import uuid

from accounts.models import User


def public_request_number():
    return f"ARI-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


class PublicCustomerRequest(models.Model):
    REQUEST_TYPES = [
        ("PURCHASE", "Product Purchase"),
        ("RENTAL", "Product Rental"),
        ("SERVICE", "RO Service"),
        ("AMC", "AMC Plan"),
        ("COMPLAINT", "Complaint"),
        ("REFERRAL", "Referral Enquiry"),
    ]
    STATUS_CHOICES = [
        ("NEW", "New"),
        ("CONTACTED", "Customer Contacted"),
        ("CONFIRMED", "Confirmed"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    PAYMENT_CHOICES = [
        ("COD", "Cash/UPI on Delivery"),
        ("OFFICE", "Confirm with ARI Team"),
    ]
    CALL_OUTCOME_CHOICES = [
        ("PENDING", "Pending"),
        ("NO_ANSWER", "No Answer"),
        ("CALLBACK", "Call Back"),
        ("INTERESTED", "Interested"),
        ("NOT_INTERESTED", "Not Interested"),
        ("WRONG_NUMBER", "Wrong Number"),
        ("CONVERTED", "Converted"),
    ]

    request_number = models.CharField(
        max_length=25,
        unique=True,
        default=public_request_number,
        editable=False,
    )
    request_type = models.CharField(max_length=15, choices=REQUEST_TYPES)
    product = models.ForeignKey(
        "products.ROModel",
        on_delete=models.PROTECT,
        related_name="public_requests",
        null=True,
        blank=True,
    )
    plan_name = models.CharField(max_length=150, blank=True)
    customer_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=10, db_index=True)
    alternate_phone = models.CharField(max_length=10, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    applied_offer = models.ForeignKey(
        "accounts.CustomerEngagement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="public_request_applications",
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default="OFFICE",
    )
    preferred_date = models.DateField(null=True, blank=True)
    referral_code = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="NEW")
    source = models.CharField(max_length=30, default="MOBILE_GUEST")
    existing_customer = models.ForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calling_leads",
    )
    priority = models.CharField(
        max_length=10,
        choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")],
        default="NORMAL",
    )
    assigned_caller = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calling_requests",
    )
    last_call_outcome = models.CharField(
        max_length=20,
        choices=CALL_OUTCOME_CHOICES,
        default="PENDING",
    )
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    last_called_at = models.DateTimeField(null=True, blank=True)
    call_count = models.PositiveIntegerField(default=0)
    call_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_number} - {self.customer_name}"


class CallingActivity(models.Model):
    lead = models.ForeignKey(
        PublicCustomerRequest,
        on_delete=models.CASCADE,
        related_name="call_activities",
    )
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calling_activities",
    )
    caller = models.ForeignKey(
        "employees.EmployeeProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calling_activities",
    )
    outcome = models.CharField(max_length=20, choices=PublicCustomerRequest.CALL_OUTCOME_CHOICES)
    note = models.TextField(blank=True, default="")
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    called_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-called_at", "-id"]

    def __str__(self):
        return f"{self.lead.request_number} - {self.outcome}"


class Customer(models.Model):

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]

    OWNERSHIP_CHOICES = [
        ("RENTAL", "Rental"),
        ("PURCHASE", "Purchased"),
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
        max_length=30,
        blank=True,
        default="",
        db_index=True,
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

    ownership_type = models.CharField(
        max_length=10,
        choices=OWNERSHIP_CHOICES,
        default="RENTAL",
    )

    rent_to_purchase_date = models.DateField(null=True, blank=True)
    rent_to_purchase_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    rent_at_conversion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    security_adjusted_at_conversion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    rent_to_purchase_notes = models.TextField(blank=True, default="")

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
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=300, blank=True, default="")

    import_batch = models.CharField(max_length=80, blank=True, default="", db_index=True)
    legacy_source_sheet = models.CharField(max_length=30, blank=True, default="")
    legacy_source_row = models.PositiveIntegerField(null=True, blank=True)
    legacy_raw_phone = models.CharField(max_length=80, blank=True, default="")
    legacy_employee = models.CharField(max_length=120, blank=True, default="")
    legacy_reference = models.CharField(max_length=150, blank=True, default="")
    legacy_installer = models.CharField(max_length=120, blank=True, default="")
    legacy_remarks = models.TextField(blank=True, default="")
    legacy_mh = models.CharField(max_length=20, blank=True, default="")
    legacy_excel_payload = models.JSONField(blank=True, default=dict)

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

    base_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    applied_offer = models.ForeignKey(
        "accounts.CustomerEngagement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rent_history_applications",
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
        ("RENT_COLLECTION", "Rent Collection"),
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

