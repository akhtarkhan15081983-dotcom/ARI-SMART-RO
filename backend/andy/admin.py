from django.contrib import admin, messages

from .models import AndyKnowledge, AndyTeaching
from .teaching import approve_teaching, reject_teaching


@admin.register(AndyTeaching)
class AndyTeachingAdmin(admin.ModelAdmin):
    list_display = (
        "id", "question_preview", "status", "submitted_by",
        "reviewed_by", "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("question", "answer", "submitted_by__phone")
    readonly_fields = (
        "submitted_by", "source_message", "question", "answer",
        "status", "reviewed_by", "reviewed_at", "knowledge",
        "created_at", "updated_at",
    )
    actions = ("approve_selected", "reject_selected")

    @admin.display(description="Question")
    def question_preview(self, obj):
        return obj.question[:100]

    @admin.action(description="Approve selected corrections")
    def approve_selected(self, request, queryset):
        approved = 0
        skipped = 0
        for row in queryset:
            try:
                approve_teaching(row.id, request.user)
                approved += 1
            except ValueError:
                skipped += 1
        self.message_user(
            request,
            f"Approved {approved}; skipped {skipped} already-reviewed submission(s).",
            messages.SUCCESS if approved else messages.WARNING,
        )

    @admin.action(description="Reject selected corrections")
    def reject_selected(self, request, queryset):
        rejected = 0
        skipped = 0
        for row in queryset:
            try:
                reject_teaching(row.id, request.user)
                rejected += 1
            except ValueError:
                skipped += 1
        self.message_user(
            request,
            f"Rejected {rejected}; skipped {skipped} already-reviewed submission(s).",
            messages.SUCCESS if rejected else messages.WARNING,
        )


@admin.register(AndyKnowledge)
class AndyKnowledgeAdmin(admin.ModelAdmin):
    list_display = ("id", "namespace", "title", "is_active", "updated_at")
    list_filter = ("namespace", "is_active")
    search_fields = ("title", "content", "source_path")
    readonly_fields = ("content_hash", "created_at", "updated_at")
