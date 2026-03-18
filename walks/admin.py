from django.contrib import admin
from .models import WalkSession, WalkSessionParticipant


class WalkParticipantInline(admin.TabularInline):
    model = WalkSessionParticipant
    extra = 0
    readonly_fields = ["joined_at", "left_at"]
    raw_id_fields = ["user"]


@admin.register(WalkSession)
class WalkSessionAdmin(admin.ModelAdmin):
    list_display = [
        "title_or_destination",
        "walk_mode",
        "status",
        "created_by",
        "member_count",
        "destination_name",
        "arrived_safely",
        "started_at",
        "ended_at",
    ]
    list_filter = [
        "walk_mode",
        "status",
        "arrived_safely",
        "monitored_by_security",
    ]
    search_fields = [
        "title",
        "destination_name",
        "created_by__full_name",
        "created_by__email",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["created_by"]
    inlines = [WalkParticipantInline]

    @admin.display(description="Walk")
    def title_or_destination(self, obj):
        return obj.title or f"→ {obj.destination_name}"

    actions = ["force_complete", "force_cancel"]

    @admin.action(description="✅ Force complete selected walks")
    def force_complete(self, request, queryset):
        from .services import end_walk
        count = 0
        for session in queryset.filter(status__in=["pending", "active"]):
            try:
                end_walk(session, ended_by=request.user)
                count += 1
            except (ValueError, Exception):
                pass
        self.message_user(request, f"✅ Completed {count} walk(s).")

    @admin.action(description="❌ Force cancel selected walks")
    def force_cancel(self, request, queryset):
        from .services import cancel_walk
        count = 0
        for session in queryset.filter(status__in=["pending", "active"]):
            try:
                cancel_walk(session, cancelled_by=request.user)
                count += 1
            except (ValueError, Exception):
                pass
        self.message_user(request, f"❌ Cancelled {count} walk(s).")


@admin.register(WalkSessionParticipant)
class WalkParticipantAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "walk_session",
        "participant_role",
        "participant_status",
        "joined_at",
        "left_at",
    ]
    list_filter = ["participant_role", "participant_status"]
    search_fields = ["user__full_name", "walk_session__destination_name"]
    raw_id_fields = ["user", "walk_session"]