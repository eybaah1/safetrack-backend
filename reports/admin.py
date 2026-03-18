from django.contrib import admin
from .models import IssueReport, ReportComment


class ReportCommentInline(admin.TabularInline):
    model = ReportComment
    extra = 0
    readonly_fields = ["created_at"]
    raw_id_fields = ["author"]


@admin.register(IssueReport)
class IssueReportAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "priority",
        "status",
        "reported_by",
        "assigned_to",
        "location_text",
        "created_at",
        "resolved_at",
    ]
    list_filter = ["status", "category", "priority", "created_at"]
    search_fields = [
        "title",
        "description",
        "location_text",
        "reported_by__full_name",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["reported_by", "assigned_to", "resolved_by"]
    inlines = [ReportCommentInline]

    fieldsets = (
        (
            "Report Info",
            {"fields": ("title", "description", "category", "priority", "status")},
        ),
        (
            "Location",
            {"fields": ("latitude", "longitude", "location_text", "photo")},
        ),
        (
            "People",
            {"fields": ("reported_by", "assigned_to", "resolved_by", "resolved_at")},
        ),
        (
            "Admin",
            {"fields": ("admin_notes",)},
        ),
        (
            "Metadata",
            {"classes": ("collapse",), "fields": ("id", "created_at", "updated_at")},
        ),
    )

    actions = ["mark_in_progress", "mark_resolved", "mark_dismissed"]

    @admin.action(description="🔄 Mark In Progress")
    def mark_in_progress(self, request, queryset):
        from .services import update_report_status
        count = 0
        for report in queryset.filter(status="open"):
            update_report_status(report, "in_progress", request.user)
            count += 1
        self.message_user(request, f"🔄 {count} report(s) marked in progress.")

    @admin.action(description="✅ Mark Resolved")
    def mark_resolved(self, request, queryset):
        from .services import update_report_status
        count = 0
        for report in queryset.filter(status__in=["open", "in_progress"]):
            update_report_status(report, "resolved", request.user)
            count += 1
        self.message_user(request, f"✅ {count} report(s) resolved.")

    @admin.action(description="🚫 Dismiss")
    def mark_dismissed(self, request, queryset):
        from .services import update_report_status
        count = 0
        for report in queryset.filter(status__in=["open", "in_progress"]):
            update_report_status(report, "dismissed", request.user)
            count += 1
        self.message_user(request, f"🚫 {count} report(s) dismissed.")


@admin.register(ReportComment)
class ReportCommentAdmin(admin.ModelAdmin):
    list_display = ["report", "author", "short_text", "is_internal", "created_at"]
    list_filter = ["is_internal", "created_at"]
    search_fields = ["comment_text", "author__full_name"]
    raw_id_fields = ["report", "author"]
    ordering = ["-created_at"]

    @admin.display(description="Comment")
    def short_text(self, obj):
        return obj.comment_text[:80]