from django.contrib import admin
from .models import Job, JobGPSLog, JobMedia

class JobGPSLogInline(admin.TabularInline):
    model = JobGPSLog
    extra = 0
    readonly_fields = (
        "latitude",
        "longitude",
        "accuracy",
        "captured_at",
    )

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "job_id",
        "customer",
        "engineer",
        "job_type",
        "priority",
        "status",
        "scheduled_date",
    )

    list_filter = (
        "job_type",
        "priority",
        "status",
    )

    search_fields = (
        "job_id",
        "customer__name",
    )

    readonly_fields = (
        "job_id",
    )

    inlines = [
        JobGPSLogInline,
    ]


@admin.register(JobMedia)
class JobMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job",
        "media_type",
        "uploaded_at",
    )

    list_filter = (
        "media_type",
        "uploaded_at",
    )

    search_fields = (
        "job__job_id",
        "description",
    )