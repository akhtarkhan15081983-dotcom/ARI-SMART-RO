from django.contrib import admin
from .models import Attendance


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