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

    # In your UserAdmin class, replace the action_approve method:

@admin.action(description="✅ Approve selected users (generates Staff ID for security)")
def action_approve(self, request, queryset):
    pending = queryset.filter(account_status="pending")

    if not pending.exists():
        self.message_user(
            request,
            "⚠️ No pending users in selection. Already approved?",
            level="warning",
        )
        return

    approved = 0
    failed = 0

    for user in pending:
        try:
            approve_user(user, approved_by=request.user)
            approved += 1
        except Exception as exc:
            failed += 1
            self.message_user(
                request,
                f"❌ Error approving {user.email}: {exc}",
                level="error",
            )

    if approved:
        self.message_user(request, f"✅ Approved {approved} user(s).")
    if failed:
        self.message_user(
            request,
            f"⚠️ {failed} user(s) failed — check Railway logs.",
            level="warning",
        )


# ← ADD THIS: New action to resend Staff ID email
@admin.action(description="📧 Resend Staff ID email to selected security users")
def action_resend_staff_email(self, request, queryset):
    """Resend the staff ID email for already-approved security users."""
    from .services import send_staff_id_email
    from .models import SecurityProfile

    count = 0
    for user in queryset:
        if user.user_role and user.user_role.strip().lower() == "security":
            profile = SecurityProfile.objects.filter(user=user).first()
            if profile:
                sent = send_staff_id_email(user, profile.staff_id)
                if sent:
                    count += 1
                    self.message_user(
                        request,
                        f"📧 Email resent to {user.email} (SID: {profile.staff_id})",
                    )
                else:
                    self.message_user(
                        request,
                        f"❌ Failed to resend to {user.email} — check logs",
                        level="error",
                    )
            else:
                self.message_user(
                    request,
                    f"⚠️ {user.email} has no SecurityProfile yet",
                    level="warning",
                )

    if count == 0:
        self.message_user(
            request,
            "No emails sent. Selected users may not be security users or lack profiles.",
            level="warning",
        )

# Don't forget to register both actions:
actions = ["action_approve", "action_reject", "action_resend_staff_email"]

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