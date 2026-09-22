from django.contrib import admin
from .models import Attendance, OvertimeRequest


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "date",
        "check_in",
        "check_out",
        "working_hours",
        "status",
    )

    list_filter = (
        "date",
        "status",
        "employee",
    )

    search_fields = (
        "employee__user__first_name",
        "employee__employee_id",
    )

    ordering = (
        "-date",
        "-check_in",
    )

@admin.register(OvertimeRequest)
class OvertimeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "attendance",
        "requested_hours",
        "approved_hours",
        "status",
        "reviewed_by",
        "started_at",
        "ended_at",
    )
    list_filter = ("status", "attendance__date")
    search_fields = (
        "attendance__employee__employee_id",
        "attendance__employee__user__first_name",
        "attendance__employee__user__phone",
        "reason",
    )
    ordering = ("-requested_at",)
