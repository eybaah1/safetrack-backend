from django.contrib import admin
from .models import SOSAlert, SOSAlertEvent
from .services import update_sos_status


class SOSAlertEventInline(admin.TabularInline):
    model = SOSAlertEvent
    extra = 0
    readonly_fields = ["event_type", "actor_user", "details", "created_at"]
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SOSAlert)
class SOSAlertAdmin(admin.ModelAdmin):
    list_display = [
        "alert_code",
        "user",
        "status",
        "location_text",
        "trigger_method",
        "triggered_at",
        "resolved_at",
    ]
    list_filter = ["status", "trigger_method", "triggered_at"]
    search_fields = [
        "alert_code",
        "user__full_name",
        "user__email",
        "location_text",
    ]
    ordering = ["-triggered_at"]
    readonly_fields = [
        "id",
        "alert_code",
        "triggered_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Alert Info",
            {
                "fields": (
                    "alert_code",
                    "user",
                    "status",
                    "trigger_method",
                    "triggered_at",
                ),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "latitude",
                    "longitude",
                    "accuracy_meters",
                    "location_text",
                ),
            },
        ),
        (
            "Resolution",
            {
                "fields": (
                    "notes",
                    "resolved_at",
                    "resolved_by",
                    "cancelled_by_user",
                    "cancelled_at",
                    "emergency_contact_notified",
                ),
            },
        ),
        (
            "Metadata",
            {
                "classes": ("collapse",),
                "fields": ("id", "created_at", "updated_at"),
            },
        ),
    )

    inlines = [SOSAlertEventInline]

    actions = ["mark_responding", "mark_resolved", "mark_false_alarm"]

    @admin.action(description="🚨 Mark as Responding")
    def mark_responding(self, request, queryset):
        count = 0
        for alert in queryset.filter(status="active"):
            try:
                update_sos_status(alert, "responding", request.user)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"🚨 {count} alert(s) marked as responding.")

    @admin.action(description="✅ Mark as Resolved")
    def mark_resolved(self, request, queryset):
        count = 0
        for alert in queryset.filter(status__in=["active", "responding"]):
            try:
                update_sos_status(alert, "resolved", request.user)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"✅ {count} alert(s) resolved.")

    @admin.action(description="⚠️ Mark as False Alarm")
    def mark_false_alarm(self, request, queryset):
        count = 0
        for alert in queryset.filter(status__in=["active", "responding"]):
            try:
                update_sos_status(alert, "false_alarm", request.user)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f"⚠️ {count} alert(s) marked as false alarm.")


@admin.register(SOSAlertEvent)
class SOSAlertEventAdmin(admin.ModelAdmin):
    list_display = [
        "sos_alert",
        "event_type",
        "actor_user",
        "created_at",
    ]
    list_filter = ["event_type", "created_at"]
    search_fields = [
        "sos_alert__alert_code",
        "actor_user__full_name",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at"]