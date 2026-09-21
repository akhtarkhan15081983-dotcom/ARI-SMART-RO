from django.db import models
from django.conf import settings
from django.utils import timezone
import secrets


class EmployeeProfile(models.Model):
    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employee_profiles",
    )

    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]

    DESIGNATION_CHOICES = [
        ("ENGINEER", "Engineer"),
        ("MANAGER", "Manager"),
        ("OFFICE", "Office Staff"),
        ("CALLING", "Calling Staff"),
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
    job_title = models.CharField(max_length=120, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")
    grade = models.CharField(max_length=50, blank=True, default="")
    reporting_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
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
    public_verification_code = models.CharField(
        max_length=24,
        unique=True,
        blank=True,
        default="",
    )
    onboarding_status = models.CharField(
        max_length=20,
        choices=[
            ("CREATED", "Created"),
            ("PROFILE_PENDING", "Profile Pending"),
            ("SECURITY_PENDING", "Security Pending"),
            ("TRAINING_PENDING", "Training Pending"),
            ("READY", "Ready"),
        ],
        default="CREATED",
    )
    id_card_valid_until = models.DateField(null=True, blank=True)
    id_card_issued_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.public_verification_code:
            while True:
                candidate = secrets.token_hex(6).upper()
                if not EmployeeProfile.objects.filter(public_verification_code=candidate).exists():
                    self.public_verification_code = candidate
                    break
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


class EmployeeCareerMovement(models.Model):
    TYPE_CHOICES = [
        ("PROMOTION", "Promotion"),
        ("DESIGNATION_CHANGE", "Designation Change"),
        ("SALARY_REVISION", "Salary Revision"),
        ("TRANSFER", "Department Transfer"),
        ("MANAGER_CHANGE", "Reporting Manager Change"),
        ("DEMOTION", "Demotion"),
        ("OTHER", "Other"),
    ]
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("APPROVED", "Approved"),
        ("CANCELLED", "Cancelled"),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="career_movements",
    )
    movement_type = models.CharField(max_length=24, choices=TYPE_CHOICES)
    effective_date = models.DateField(default=timezone.localdate)
    old_designation = models.CharField(max_length=20, blank=True, default="")
    new_designation = models.CharField(max_length=20, blank=True, default="")
    old_job_title = models.CharField(max_length=120, blank=True, default="")
    new_job_title = models.CharField(max_length=120, blank=True, default="")
    old_department = models.CharField(max_length=100, blank=True, default="")
    new_department = models.CharField(max_length=100, blank=True, default="")
    old_grade = models.CharField(max_length=50, blank=True, default="")
    new_grade = models.CharField(max_length=50, blank=True, default="")
    old_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    new_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    old_reporting_manager = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="career_movements_as_old_manager",
    )
    new_reporting_manager = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="career_movements_as_new_manager",
    )
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="DRAFT")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_career_movements",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_career_movements",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
        indexes = [
            models.Index(fields=["employee", "effective_date"], name="emp_career_emp_date_idx"),
            models.Index(fields=["status", "effective_date"], name="emp_career_status_idx"),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.movement_type} - {self.effective_date}"


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


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True, default="")
    is_paid = models.BooleanField(default=True)
    declared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="declared_holidays",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} - {self.name}"


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


class EmployeePenalty(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("APPROVED", "Approved"),
        ("CANCELLED", "Cancelled"),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="penalties",
    )
    penalty_date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="DRAFT")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_employee_penalties",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_employee_penalties",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-penalty_date", "-created_at"]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.amount} - {self.status}"


class PerformanceReview(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("FINAL", "Final"),
        ("ACKNOWLEDGED", "Acknowledged"),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="performance_reviews",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performance_reviews_given",
    )
    goals_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    attendance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    service_quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    customer_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sales_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    strengths = models.TextField(blank=True, default="")
    improvement_plan = models.TextField(blank=True, default="")
    comments = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="DRAFT")
    finalized_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_end", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period_start", "period_end"],
                name="unique_employee_performance_period",
            )
        ]

    def recalculate(self):
        values = [
            self.goals_score,
            self.attendance_score,
            self.service_quality_score,
            self.customer_score,
            self.sales_score,
        ]
        self.overall_score = sum(values) / len(values)
        return self.overall_score




class TrainingCourse(models.Model):
    AUDIENCE_CHOICES = [
        ("ALL", "All Employees"),
        ("ENGINEER", "Engineer"),
        ("MANAGER", "Manager"),
        ("OFFICE", "Office Staff"),
        ("CALLING", "Calling Staff"),
    ]

    company = models.ForeignKey(
        "tenancy.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="training_courses",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True, default="")
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default="ALL")
    is_mandatory = models.BooleanField(default=True)
    passing_score = models.PositiveIntegerField(default=80)
    due_days = models.PositiveIntegerField(default=7)
    grace_days = models.PositiveIntegerField(default=2)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    certificate_enabled = models.BooleanField(default=True)
    certificate_valid_days = models.PositiveIntegerField(default=365)
    required_trainer_reviews = models.PositiveSmallIntegerField(default=0)
    minimum_trainer_average = models.DecimalField(max_digits=3, decimal_places=2, default=3.00)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_training_courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class TrainingLesson(models.Model):
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="lessons")
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=180)
    content = models.TextField()
    key_takeaway = models.CharField(max_length=300, blank=True, default="")
    video_asset = models.CharField(max_length=255, blank=True, default="")
    video_url = models.URLField(max_length=500, blank=True, default="")
    resource_url = models.URLField(max_length=500, blank=True, default="")
    resource_label = models.CharField(max_length=120, blank=True, default="")
    day_number = models.PositiveSmallIntegerField(default=1)
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    trainer_script = models.TextField(blank=True, default="")
    practice_task = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["course", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "order"], name="unique_training_lesson_order")
        ]

    def __str__(self):
        return f"{self.course.title} • {self.title}"


class TrainingQuestion(models.Model):
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=1)
    question = models.CharField(max_length=500)
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)
    correct_option = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
    )
    explanation = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["course", "order", "id"]

    def __str__(self):
        return self.question[:80]


class EmployeeTrainingAssignment(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("OVERDUE", "Overdue"),
    ]

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="training_assignments",
    )
    course = models.ForeignKey(
        TrainingCourse,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    grace_until = models.DateField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    lessons_completed = models.JSONField(default=list, blank=True)
    quiz_score = models.PositiveIntegerField(default=0)
    attempts = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    compliance_strike = models.BooleanField(default=False)
    penalty_created = models.BooleanField(default=False)
    penalty = models.ForeignKey(
        EmployeePenalty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_assignments",
    )

    class Meta:
        ordering = ["status", "due_date", "-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "course"],
                name="unique_employee_training_course",
            )
        ]

    def __str__(self):
        return f"{self.employee.employee_id} • {self.course.title}"


class TrainingTrainerReview(models.Model):
    assignment = models.ForeignKey(
        EmployeeTrainingAssignment,
        on_delete=models.CASCADE,
        related_name="trainer_reviews",
    )
    lesson = models.ForeignKey(
        TrainingLesson,
        on_delete=models.CASCADE,
        related_name="trainer_reviews",
    )
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="training_reviews_given",
    )
    behaviour_score = models.PositiveSmallIntegerField(default=3)
    communication_score = models.PositiveSmallIntegerField(default=3)
    knowledge_score = models.PositiveSmallIntegerField(default=3)
    strengths = models.TextField(blank=True, default="")
    gaps = models.TextField(blank=True, default="")
    coaching_action = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lesson__day_number", "lesson__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "lesson"],
                name="unique_training_trainer_review",
            )
        ]

    def __str__(self):
        return f"{self.assignment} • Day {self.lesson.day_number}"


class TrainingCertificate(models.Model):
    assignment = models.OneToOneField(
        EmployeeTrainingAssignment,
        on_delete=models.CASCADE,
        related_name="certificate",
    )
    certificate_number = models.CharField(max_length=40, unique=True)
    verification_code = models.CharField(max_length=48, unique=True)
    quiz_score = models.PositiveIntegerField(default=0)
    trainer_average = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    final_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="training_certificates_issued",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="training_certificates_revoked",
    )
    revoke_reason = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.certificate_number} • {self.assignment.employee.employee_id}"


class EmployeeDocument(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="hr_documents")
    document_type = models.CharField(max_length=50)
    document_number = models.CharField(max_length=100, blank=True, default="")
    file = models.FileField(upload_to="employees/documents/", blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
