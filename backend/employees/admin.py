from django.contrib import admin
from .models import EmployeeDocument, EmployeeProfile, HRPolicy, LeaveRequest, PayrollRecord


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


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ("employee", "payroll_month", "base_salary", "late_penalty", "overtime_amount", "rent_incentive", "sale_incentive", "net_salary", "status")
    list_filter = ("status", "payroll_month")
    search_fields = ("employee__employee_id", "employee__user__first_name", "employee__user__phone")
    readonly_fields = ("calculation_snapshot", "created_at", "updated_at", "approved_at", "paid_at")


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "document_type", "document_number", "expiry_date", "verified", "uploaded_at")
    list_filter = ("document_type", "verified", "expiry_date")
    search_fields = ("employee__employee_id", "employee__user__first_name", "document_number")
