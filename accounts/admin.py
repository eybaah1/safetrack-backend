from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, StudentProfile, SecurityProfile, EmergencyContact, SavedLocation
from .services import approve_user, reject_user


# ────────────────────────────────────────────────────────
# Inlines
# ────────────────────────────────────────────────────────
class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    extra = 0


class SecurityProfileInline(admin.StackedInline):
    model = SecurityProfile
    can_delete = False
    extra = 0
    readonly_fields = ["staff_id", "created_at"]


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


# ────────────────────────────────────────────────────────
# User Admin
# ────────────────────────────────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "full_name",
        "user_role",
        "account_status",
        "phone",
        "hostel_name",
        "created_at",
    ]
    list_filter = ["user_role", "account_status", "gender", "hostel_name"]
    search_fields = ["email", "full_name", "phone"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "approved_by", "approved_at", "last_login"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Info",
            {"fields": ("full_name", "phone", "gender", "hostel_name", "town", "landmark")},
        ),
        (
            "Role & Status",
            {"fields": ("user_role", "account_status", "approved_by", "approved_at")},
        ),
        (
            "Verification",
            {
                "fields": (
                    "email_verified",
                    "phone_verified",
                    "profile_photo",
                    "profile_photo_verified",
                ),
            },
        ),
        (
            "Django Permissions",
            {
                "classes": ("collapse",),
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (
            "Timestamps",
            {"classes": ("collapse",), "fields": ("last_login", "created_at", "updated_at")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone",
                    "user_role",
                    "gender",
                    "hostel_name",
                    "town",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    inlines = [StudentProfileInline, SecurityProfileInline, EmergencyContactInline]

    # ── Custom admin actions ────────────────────────────
    actions = ["action_approve", "action_reject"]

    @admin.action(description="✅ Approve selected users (generates Staff ID for security)")
    def action_approve(self, request, queryset):
        pending = queryset.filter(account_status="pending")
        count = 0
        for user in pending:
            try:
                approve_user(user, approved_by=request.user)
                count += 1
            except Exception as exc:
                self.message_user(
                    request,
                    f"Error approving {user.email}: {exc}",
                    level="error",
                )
        self.message_user(request, f"✅ Approved {count} user(s).")

    @admin.action(description="❌ Reject selected users")
    def action_reject(self, request, queryset):
        pending = queryset.filter(account_status="pending")
        count = 0
        for user in pending:
            reject_user(user)
            count += 1
        self.message_user(request, f"❌ Rejected {count} user(s).")


# ────────────────────────────────────────────────────────
# Standalone model admins
# ────────────────────────────────────────────────────────
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "student_id", "created_at"]
    search_fields = ["student_id", "user__full_name", "user__email"]


@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "staff_id", "is_on_duty", "created_at"]
    search_fields = ["staff_id", "user__full_name", "user__email"]
    list_filter = ["is_on_duty"]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ["contact_name", "user", "relationship", "phone", "priority_order"]
    list_filter = ["notify_for_sos"]
    search_fields = ["contact_name", "user__full_name"]


@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = ["label", "user", "is_default", "created_at"]
    search_fields = ["label", "user__full_name"]