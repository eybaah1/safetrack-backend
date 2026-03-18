from django.contrib import admin
from .models import PatrolUnit, PatrolUnitMember, SOSAssignment


class PatrolUnitMemberInline(admin.TabularInline):
    model = PatrolUnitMember
    extra = 0
    raw_id_fields = ["security_user"]


@admin.register(PatrolUnit)
class PatrolUnitAdmin(admin.ModelAdmin):
    list_display = [
        "unit_name",
        "status",
        "area_of_patrol",
        "member_count",
        "current_lat",
        "current_lng",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["unit_name", "area_of_patrol"]
    ordering = ["unit_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [PatrolUnitMemberInline]

    actions = ["set_available", "set_offline"]

    @admin.action(description="✅ Set Available")
    def set_available(self, request, queryset):
        count = queryset.update(status="available")
        self.message_user(request, f"✅ {count} unit(s) set to available.")

    @admin.action(description="🔴 Set Offline")
    def set_offline(self, request, queryset):
        count = queryset.update(status="offline")
        self.message_user(request, f"🔴 {count} unit(s) set to offline.")


@admin.register(PatrolUnitMember)
class PatrolUnitMemberAdmin(admin.ModelAdmin):
    list_display = ["security_user", "patrol_unit", "is_lead", "joined_at"]
    list_filter = ["is_lead", "patrol_unit"]
    search_fields = ["security_user__full_name", "patrol_unit__unit_name"]
    raw_id_fields = ["security_user"]


@admin.register(SOSAssignment)
class SOSAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "sos_alert",
        "responder_name",
        "status",
        "assigned_by",
        "assigned_at",
        "on_scene_at",
        "closed_at",
    ]
    list_filter = ["status", "assigned_at"]
    search_fields = [
        "sos_alert__alert_code",
        "patrol_unit__unit_name",
        "security_user__full_name",
    ]
    ordering = ["-assigned_at"]
    readonly_fields = ["id", "assigned_at", "created_at", "updated_at"]
    raw_id_fields = ["sos_alert", "patrol_unit", "security_user", "assigned_by"]