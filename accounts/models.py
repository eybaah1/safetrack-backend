import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from common.models import TimeStampedUUIDModel
from common.validators import latitude_validators, longitude_validators
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.
    Students log in with email + password.
    Security log in with staff_id + password (staff_id issued on approval).
    """

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        SECURITY = "security", "Security"
        ADMIN = "admin", "Admin"

    class AccountStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    class Gender(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        PREFER_NOT_TO_SAY = "Prefer not to say", "Prefer not to say"

    # ── Identity ────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    user_role = models.CharField(max_length=20, choices=Role.choices)
    gender = models.CharField(max_length=20, choices=Gender.choices)

    # ── Location info ───────────────────────────────────
    hostel_name = models.CharField(max_length=150)
    town = models.CharField(max_length=100)
    landmark = models.CharField(max_length=150, blank=True, default="")

    # ── Profile photo ───────────────────────────────────
    profile_photo = models.ImageField(
        upload_to="profile_photos/", blank=True, null=True
    )
    profile_photo_verified = models.BooleanField(default=False)

    # ── Account status ──────────────────────────────────
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
    )
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # ── Approval ────────────────────────────────────────
    approved_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_users",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # ── Django auth fields ──────────────────────────────
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # ── Timestamps ──────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]  # minimal — for createsuperuser prompt

    class Meta:
        db_table = "app_users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.get_user_role_display()})"

    # ── Convenience properties ──────────────────────────
    @property
    def is_student(self):
        return self.user_role == self.Role.STUDENT

    @property
    def is_security(self):
        return self.user_role == self.Role.SECURITY

    @property
    def is_admin_user(self):
        return self.user_role == self.Role.ADMIN

    @property
    def is_approved(self):
        return self.account_status == self.AccountStatus.APPROVED


# ────────────────────────────────────────────────────────
# Role-specific profiles
# ────────────────────────────────────────────────────────
class StudentProfile(models.Model):
    """Created immediately on student sign-up."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="student_profile"
    )
    student_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_profiles"

    def __str__(self):
        return f"{self.user.full_name} — {self.student_id}"


class SecurityProfile(models.Model):
    """Created only when an admin APPROVES a security user.
    staff_id is auto-generated and sent via SMS.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="security_profile"
    )
    staff_id = models.CharField(max_length=50, unique=True)
    badge_number = models.CharField(max_length=50, blank=True, default="")
    is_on_duty = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "security_profiles"

    def __str__(self):
        return f"{self.user.full_name} — {self.staff_id}"


# ────────────────────────────────────────────────────────
# Emergency Contacts & Saved Locations
# ────────────────────────────────────────────────────────
class EmergencyContact(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    contact_name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, default="")
    notify_for_sos = models.BooleanField(default=True)
    priority_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "emergency_contacts"
        ordering = ["priority_order"]

    def __str__(self):
        return f"{self.contact_name} ({self.relationship})"


class SavedLocation(TimeStampedUUIDModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_locations"
    )
    label = models.CharField(max_length=100)
    address_text = models.CharField(max_length=255, blank=True, default="")
    latitude = models.FloatField(
        null=True, blank=True, validators=latitude_validators
    )
    longitude = models.FloatField(
        null=True, blank=True, validators=longitude_validators
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "saved_locations"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label} — {self.user.full_name}"
    

class PasswordResetCode(models.Model):
    """
    Stores a 6-digit code sent to user's email for password reset.
    Expires after 15 minutes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_codes")
    code = models.CharField(max_length=6)
    email = models.EmailField()
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_codes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reset code for {self.email} ({'used' if self.is_used else 'active'})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired