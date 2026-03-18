from django.contrib import admin
from .models import Notification, BroadcastAlert, UserDevice, UserPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "user",
        "notification_type",
        "is_read",
        "sent_via_push",
        "sent_via_ws",
        "created_at",
    ]
    list_filter = ["notification_type", "is_read", "sent_via_push", "created_at"]
    search_fields = ["title", "message", "user__full_name", "user__email"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user"]
    list_per_page = 50

    actions = ["mark_read", "mark_unread"]

    @admin.action(description="✓ Mark as read")
    def mark_read(self, request, queryset):
        from .services import mark_notification_read
        count = 0
        for notif in queryset.filter(is_read=False):
            mark_notification_read(notif)
            count += 1
        self.message_user(request, f"✓ Marked {count} as read.")

    @admin.action(description="● Mark as unread")
    def mark_unread(self, request, queryset):
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"● Marked {count} as unread.")


@admin.register(BroadcastAlert)
class BroadcastAlertAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "alert_type",
        "location",
        "audience",
        "is_active",
        "published_by",
        "expires_at",
        "created_at",
    ]
    list_filter = ["alert_type", "is_active", "audience", "created_at"]
    search_fields = ["title", "message", "location"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["published_by"]

    actions = ["activate", "deactivate"]

    @admin.action(description="🟢 Activate")
    def activate(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"🟢 Activated {count} alert(s).")

    @admin.action(description="⚪ Deactivate")
    def deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"⚪ Deactivated {count} alert(s).")


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "push_provider", "device_name", "is_active", "last_seen_at"]
    list_filter = ["platform", "push_provider", "is_active"]
    search_fields = ["user__full_name", "user__email", "device_name"]
    raw_id_fields = ["user"]


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "notifications_enabled",
        "sos_alerts_enabled",
        "sound_alerts_enabled",
        "dark_mode_enabled",
        "updated_at",
    ]
    search_fields = ["user__full_name", "user__email"]