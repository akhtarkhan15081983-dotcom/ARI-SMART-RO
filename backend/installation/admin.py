from django.contrib import admin

from .models import (
    Installation,
    InstallationPhoto,
    InstallationVideo,
    InstallationSignature,
    InstallationPart,
)


class InstallationPhotoInline(admin.TabularInline):
    model = InstallationPhoto
    extra = 0


class InstallationPartInline(admin.TabularInline):
    model = InstallationPart
    extra = 0


@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):

    list_display = (
        "installation_id",
        "job",
        "customer",
        "ro_asset",
        "engineer",
        "business_type",
        "status",
        "scheduled_date",
    )

    readonly_fields = (
        "installation_id",
    )

    list_filter = (
        "status",
        "scheduled_date",
    )

    search_fields = (
        "job__job_id",
        "customer__name",
        "ro_asset__asset_id",
    )

    exclude = (
        "completed_date",
        "status",
    )

    # Future:
    # inlines = [
    #     InstallationPhotoInline,
    #     InstallationPartInline,
    # ]