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

    employee_id = models.CharField(max_length=20, unique=True)

    photo = models.ImageField(
        upload_to="employees/",
        blank=True,
        null=True,
    )

    face_enrolled_at = models.DateTimeField(null=True, blank=True)
    face_enrollment_verified = models.BooleanField(default=False)
    face_enrollment_allowed = models.BooleanField(default=False)

    attendance_device_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
    )

    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    aadhaar_number = models.CharField(max_length=12, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    joining_date = models.DateField()

    designation = models.CharField(
        max_length=20,
        choices=DESIGNATION_CHOICES,
    )

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    emergency_contact = models.CharField(max_length=10, blank=True)
    emergency_name = models.CharField(max_length=100, blank=True)

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
    last_location_updated = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
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
            self.employee_id = f"EMP-{year}-{last_number + 1:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.user.get_full_name()}"


class HRPolicy(models.Model):
    office_start_time = models.TimeField(default="10:00")
    daily_work_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8)
    late_penalty_amount = models.DecimalField(max_digits=8, decimal_places=2, default=50)
    half_day_cutoff = models.TimeField(default="12:00")
    monthly_paid_leaves = models.PositiveSmallIntegerField(default=2)
    monthly_paid_half_days = models.PositiveSmallIntegerField(default=2)
    leave_notice_days = models.PositiveSmallIntegerField(default=1)
    rent_installation_monthly_incentive = models.DecimalField(max_digits=8, decimal_places=2, default=50)
    rent_installation_incentive_months = models.PositiveSmallIntegerField(default=12)
    sale_installation_incentive = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return "ARI HR & Payroll Policy"


class LeaveRequest(models.Model):
    TYPE_CHOICES = [("FULL_DAY", "Full Day"), ("HALF_DAY", "Half Day")]
    STATUS_CHOICES = [("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")]
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(max_length=500)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="PENDING")
    is_paid = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_leaves")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]


class PayrollRecord(models.Model):
    STATUS_CHOICES = [("DRAFT", "Draft"), ("APPROVED", "Approved"), ("PAID", "Paid")]
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name="payroll_records")
    payroll_month = models.DateField(help_text="First day of payroll month")
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payable_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    late_days = models.PositiveIntegerField(default=0)
    late_penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    half_day_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    absence_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rent_incentive = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sale_incentive = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calculation_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="DRAFT")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_payrolls")
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-payroll_month", "employee__employee_id"]
        constraints = [models.UniqueConstraint(fields=["employee", "payroll_month"], name="unique_employee_payroll_month")]


class EmployeeDocument(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="hr_documents")
    document_type = models.CharField(max_length=50)
    document_number = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="employees/documents/", blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
