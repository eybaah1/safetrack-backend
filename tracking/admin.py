from django.contrib import admin
from .models import UserLiveLocation, LocationHistory


@admin.register(UserLiveLocation)
class UserLiveLocationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "latitude",
        "longitude",
        "is_sharing",
        "source",
        "accuracy_meters",
        "updated_at",
    ]
    list_filter = ["is_sharing", "source"]
    search_fields = ["user__full_name", "user__email"]
    ordering = ["-updated_at"]
    readonly_fields = ["updated_at"]

    actions = ["stop_sharing"]

    @admin.action(description="🔴 Stop sharing for selected users")
    def stop_sharing(self, request, queryset):
        count = queryset.update(is_sharing=False)
        self.message_user(request, f"🔴 Stopped sharing for {count} user(s).")


@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "context",
        "reference_id",
        "latitude",
        "longitude",
        "recorded_at",
    ]
    list_filter = ["context", "recorded_at"]
    search_fields = ["user__full_name", "user__email"]
    ordering = ["-recorded_at"]
    readonly_fields = ["id", "recorded_at"]

    # Don't load all history in admin
    list_per_page = 50