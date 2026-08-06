from django.contrib import admin
from .models import EmployeeProfile


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