from django.contrib import admin
from .models import EmployeeCareerMovement, EmployeeDocument, EmployeePenalty, EmployeeProfile, Holiday, HRPolicy, LeaveRequest, PayrollRecord, PerformanceReview


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):

    list_display = (
        "employee_id",
        "user",
        "designation",
        "joining_date",
        "is_active",
    )

    search_fields = (
        "employee_id",
        "user__phone",
        "user__first_name",
    )

    list_filter = (
        "designation",
        "is_active",
    )


@admin.register(HRPolicy)
class HRPolicyAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Attendance & Leave", {"fields": ("office_start_time", "half_day_cutoff", "daily_work_hours", "late_penalty_amount", "monthly_paid_leaves", "monthly_paid_half_days", "leave_notice_days")}),
        ("Incentives", {"fields": ("rent_installation_monthly_incentive", "rent_installation_incentive_months", "sale_installation_incentive")}),
    )

    def has_add_permission(self, request):
        return not HRPolicy.objects.exists()


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "status", "is_paid", "reviewed_by")
    list_filter = ("status", "leave_type", "is_paid", "start_date")
    search_fields = ("employee__employee_id", "employee__user__first_name", "employee__user__phone", "reason")
    readonly_fields = ("created_at", "reviewed_at")


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ("date", "name", "is_paid", "declared_by")
    list_filter = ("is_paid", "date")
    search_fields = ("name", "description")
    readonly_fields = ("declared_by", "created_at")

    def save_model(self, request, obj, form, change):
        if not obj.declared_by_id:
            obj.declared_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "payroll_month", "base_salary", "late_penalty", "short_hours_deduction", "overtime_amount", "rent_incentive", "sale_incentive", "net_salary", "status")
    list_filter = ("status", "payroll_month")
    search_fields = ("employee__employee_id", "employee__user__first_name", "employee__user__phone")
    readonly_fields = ("calculation_snapshot", "created_at", "updated_at", "approved_at", "paid_at")


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "document_type", "document_number", "expiry_date", "verified", "uploaded_at")
    list_filter = ("document_type", "verified", "expiry_date")
    search_fields = ("employee__employee_id", "employee__user__first_name", "document_number")


@admin.register(EmployeePenalty)
class EmployeePenaltyAdmin(admin.ModelAdmin):
    list_display = ("employee", "penalty_date", "amount", "reason", "status", "created_by", "approved_by")
    list_filter = ("status", "penalty_date")
    search_fields = ("employee__employee_id", "employee__user__first_name", "employee__user__phone", "reason")
    readonly_fields = ("created_by", "approved_by", "approved_at", "cancelled_at", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(EmployeeCareerMovement)
class EmployeeCareerMovementAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "movement_type", "effective_date", "old_job_title",
        "new_job_title", "old_salary", "new_salary", "status", "approved_by",
    )
    list_filter = ("movement_type", "status", "effective_date")
    search_fields = (
        "employee__employee_id", "employee__user__first_name",
        "employee__user__phone", "new_job_title", "new_department", "reason",
    )
    readonly_fields = (
        "old_designation", "old_job_title", "old_department", "old_grade",
        "old_salary", "old_reporting_manager", "created_by", "approved_by",
        "approved_at", "cancelled_at", "created_at",
    )


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "period_start", "period_end", "overall_score",
        "status", "reviewer", "finalized_at", "acknowledged_at",
    )
    list_filter = ("status", "period_start", "period_end")
    search_fields = (
        "employee__employee_id", "employee__user__first_name",
        "employee__user__phone", "strengths", "improvement_plan",
    )
    readonly_fields = ("overall_score", "created_at", "updated_at", "finalized_at", "acknowledged_at")
