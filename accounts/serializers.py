from rest_framework import serializers
from django.contrib.auth import password_validation

from .models import (
    User,
    StudentProfile,
    SecurityProfile,
    EmergencyContact,
    SavedLocation,
)


# ────────────────────────────────────────────────────────
# Auth serializers
# ────────────────────────────────────────────────────────
class SignUpSerializer(serializers.Serializer):
    """
    Handles both student and security sign-up.
    Students must supply student_id.
    Security does NOT supply staff_id (it's generated on approval).
    """

    user_type = serializers.ChoiceField(choices=["student", "security"])
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    gender = serializers.ChoiceField(choices=User.Gender.choices)
    hostel_name = serializers.CharField(max_length=150)
    town = serializers.CharField(max_length=100)
    landmark = serializers.CharField(max_length=150, required=False, default="")

    # Student-only
    student_id = serializers.CharField(max_length=50, required=False)

    # Optional photo (multipart upload)
    profile_photo = serializers.ImageField(required=False)

    # ── Validation ──────────────────────────────────────
    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate(self, data):
        # Passwords must match
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        # Validate password strength
        password_validation.validate_password(data["password"])

        # Student must provide student_id
        if data["user_type"] == "student":
            sid = data.get("student_id", "").strip()
            if not sid:
                raise serializers.ValidationError(
                    {"student_id": "Student ID is required."}
                )
            if StudentProfile.objects.filter(student_id=sid).exists():
                raise serializers.ValidationError(
                    {"student_id": "This Student ID is already registered."}
                )

        return data

    # ── Create ──────────────────────────────────────────
    def create(self, validated_data):
        user_type = validated_data.pop("user_type")
        student_id = validated_data.pop("student_id", None)
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        profile_photo = validated_data.pop("profile_photo", None)

        user = User(
            user_role=user_type,
            # Students are auto-approved; security must wait for admin
            account_status="approved" if user_type == "student" else "pending",
            **validated_data,
        )
        user.set_password(password)
        if profile_photo:
            user.profile_photo = profile_photo
        user.save()

        # Create student profile immediately
        if user_type == "student" and student_id:
            StudentProfile.objects.create(user=user, student_id=student_id.strip())

        return user


class LoginSerializer(serializers.Serializer):
    """
    Students  → user_type='student',  identifier=email
    Security  → user_type='security', identifier=staff_id (SID-XXXX)
    """

    user_type = serializers.ChoiceField(choices=["student", "security"])
    identifier = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user_type = data["user_type"]
        identifier = data["identifier"].strip()
        password = data["password"]

        user = None

        if user_type == "student":
            try:
                user = User.objects.get(email__iexact=identifier, user_role="student")
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password.")

        elif user_type == "security":
            try:
                profile = (
                    SecurityProfile.objects
                    .select_related("user")
                    .get(staff_id=identifier)
                )
                user = profile.user
            except SecurityProfile.DoesNotExist:
                raise serializers.ValidationError("Invalid Staff ID or password.")

        # Check password
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        # Check account flags
        if not user.is_active:
            raise serializers.ValidationError("Account has been deactivated.")

        status = user.account_status
        if status == "pending":
            raise serializers.ValidationError(
                "Your account is pending admin approval."
            )
        if status == "rejected":
            raise serializers.ValidationError(
                "Your account request was rejected. Contact admin."
            )
        if status == "suspended":
            raise serializers.ValidationError("Your account has been suspended.")

        data["user"] = user
        return data


# ────────────────────────────────────────────────────────
# User profile serializer
# ────────────────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    student_id = serializers.SerializerMethodField()
    staff_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "user_role",
            "gender",
            "hostel_name",
            "town",
            "landmark",
            "profile_photo",
            "profile_photo_verified",
            "account_status",
            "email_verified",
            "phone_verified",
            "student_id",
            "staff_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "user_role",
            "account_status",
            "profile_photo_verified",
            "email_verified",
            "phone_verified",
            "student_id",
            "staff_id",
            "created_at",
            "updated_at",
        ]

    def get_student_id(self, obj):
        if hasattr(obj, "student_profile"):
            return obj.student_profile.student_id
        return None

    def get_staff_id(self, obj):
        if hasattr(obj, "security_profile"):
            return obj.security_profile.staff_id
        return None


class ProfilePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["profile_photo"]


# ────────────────────────────────────────────────────────
# Emergency contacts
# ────────────────────────────────────────────────────────
class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id",
            "contact_name",
            "relationship",
            "phone",
            "email",
            "notify_for_sos",
            "priority_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ────────────────────────────────────────────────────────
# Saved locations
# ────────────────────────────────────────────────────────
class SavedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedLocation
        fields = [
            "id",
            "label",
            "address_text",
            "latitude",
            "longitude",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ────────────────────────────────────────────────────────
# Password Reset
# ────────────────────────────────────────────────────────
class RequestResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data