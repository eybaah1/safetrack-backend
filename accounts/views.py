from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from common.permissions import IsAdmin
from .models import User, EmergencyContact, SavedLocation
from .serializers import (
    SignUpSerializer,
    LoginSerializer,
    UserSerializer,
    ProfilePhotoSerializer,
    EmergencyContactSerializer,
    SavedLocationSerializer,
    RequestResetCodeSerializer,
    VerifyResetCodeSerializer,
    ResetPasswordSerializer,
)
from .services import approve_user, reject_user, send_reset_code_email, verify_reset_code, reset_password_with_code


# ════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════
class SignUpView(generics.CreateAPIView):
    """
    POST /api/v1/auth/signup/
    Students are auto-approved and receive tokens.
    Security accounts are created as 'pending'.
    """

    serializer_class = SignUpSerializer
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, MultiPartParser, FormParser]  # ← JSON first

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_data = {
            "user": UserSerializer(user).data,
        }

        if user.is_approved:
            # Student — auto-approved, return tokens
            refresh = RefreshToken.for_user(user)
            response_data["message"] = "Account created successfully."
            response_data["tokens"] = {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        else:
            # Security — pending
            response_data["message"] = (
                "Account created. You will receive your Staff ID via SMS "
                "once an admin approves your request."
            )

        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """
    POST /api/v1/auth/login/
    Body: { user_type, identifier, password }

    Students  → identifier = email
    Security  → identifier = SID-XXXX
    """

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "user": UserSerializer(user).data,
            }
        )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Body: { refresh }
    Blacklists the refresh token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        return Response({"message": "Logged out."}, status=status.HTTP_200_OK)


# ════════════════════════════════════════════════════════
# CURRENT USER PROFILE (ME)
# ════════════════════════════════════════════════════════
class MeView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/auth/me/         — fetch my profile
    PATCH /api/v1/auth/me/         — update editable fields
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class MePhotoView(generics.UpdateAPIView):
    """
    PATCH /api/v1/auth/me/photo/   — upload or replace profile photo
    """

    serializer_class = ProfilePhotoSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user


# ════════════════════════════════════════════════════════
# EMERGENCY CONTACTS
# ════════════════════════════════════════════════════════
class EmergencyContactViewSet(viewsets.ModelViewSet):
    """
    /api/v1/auth/me/emergency-contacts/
    /api/v1/auth/me/emergency-contacts/<id>/
    """

    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ════════════════════════════════════════════════════════
# SAVED LOCATIONS
# ════════════════════════════════════════════════════════
class SavedLocationViewSet(viewsets.ModelViewSet):
    """
    /api/v1/auth/me/saved-locations/
    /api/v1/auth/me/saved-locations/<id>/
    """

    serializer_class = SavedLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedLocation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ════════════════════════════════════════════════════════
# ADMIN — User Approval (for dashboard frontend)
# ════════════════════════════════════════════════════════
class PendingUsersView(generics.ListAPIView):
    """
    GET /api/v1/auth/admin/pending-users/
    Returns all users with status='pending'.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return User.objects.filter(account_status="pending").order_by("-created_at")


class ApproveUserView(APIView):
    """
    POST /api/v1/auth/admin/users/<user_id>/approve/
    Approves a pending user.
    If security → generates staff_id and sends SMS.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, account_status="pending")
        except User.DoesNotExist:
            return Response(
                {"error": "User not found or not in pending status."},
                status=status.HTTP_404_NOT_FOUND,
            )

        approved = approve_user(user, approved_by=request.user)

        msg = f"{approved.full_name} has been approved."
        if approved.is_security:
            staff_id = approved.security_profile.staff_id
            msg += f" Staff ID ({staff_id}) sent via SMS."

        return Response(
            {"message": msg, "user": UserSerializer(approved).data},
            status=status.HTTP_200_OK,
        )


class RejectUserView(APIView):
    """
    POST /api/v1/auth/admin/users/<user_id>/reject/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, account_status="pending")
        except User.DoesNotExist:
            return Response(
                {"error": "User not found or not in pending status."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reject_user(user)
        return Response(
            {"message": f"{user.full_name} has been rejected."},
            status=status.HTTP_200_OK,
        )
    

# ════════════════════════════════════════════════════════
# PASSWORD RESET
# ════════════════════════════════════════════════════════
class RequestResetCodeView(APIView):
    """
    POST /api/v1/auth/forgot-password/
    Sends a 6-digit code to the user's email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response(
                {"message": "If an account with this email exists, a reset code has been sent."},
                status=status.HTTP_200_OK,
            )

        try:
            send_reset_code_email(user)
        except Exception:
            return Response(
                {"error": "Failed to send email. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"message": "If an account with this email exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )


class VerifyResetCodeView(APIView):
    """
    POST /api/v1/auth/verify-reset-code/
    Verifies the 6-digit code without resetting password yet.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, _ = verify_reset_code(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
            )
            return Response(
                {"message": "Code verified.", "valid": True},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"error": str(e), "valid": False},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/
    Verifies code and sets new password.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = reset_password_with_code(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
                new_password=serializer.validated_data["new_password"],
            )
            return Response(
                {"message": "Password reset successful. You can now sign in."},
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )