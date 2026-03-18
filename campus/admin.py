from django.contrib import admin
from .models import CampusLocation


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "location_type",
        "area",
        "safety_rating",
        "lighting",
        "is_active",
        "is_popular",
    ]
    list_filter = [
        "location_type",
        "area",
        "lighting",
        "security_presence",
        "is_active",
        "is_popular",
    ]
    search_fields = ["name", "area", "description"]
    ordering = ["name"]

    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "location_type",
                    "area",
                    "description",
                ),
            },
        ),
        (
            "Coordinates",
            {
                "fields": ("latitude", "longitude"),
            },
        ),
        (
            "Safety Information",
            {
                "fields": (
                    "safety_rating",
                    "lighting",
                    "security_presence",
                    "recent_activity",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "is_popular"),
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

    actions = ["mark_popular", "mark_not_popular", "deactivate", "activate"]

    @admin.action(description="⭐ Mark as popular")
    def mark_popular(self, request, queryset):
        count = queryset.update(is_popular=True)
        self.message_user(request, f"⭐ {count} location(s) marked as popular.")

    @admin.action(description="Remove from popular")
    def mark_not_popular(self, request, queryset):
        count = queryset.update(is_popular=False)
        self.message_user(request, f"{count} location(s) removed from popular.")

    @admin.action(description="🚫 Deactivate")
    def deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"🚫 {count} location(s) deactivated.")

    @admin.action(description="✅ Activate")
    def activate(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"✅ {count} location(s) activated.")