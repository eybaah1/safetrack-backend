import logging
import random

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────
# Phone formatting
# ────────────────────────────────────────────────────────
def format_phone_e164(phone: str) -> str:
    """
    Convert a Ghana-style phone number to E.164 format.
    '024 123 4567'  →  '+233241234567'
    '0241234567'    →  '+233241234567'
    '+233241234567' →  '+233241234567'
    """
    phone = phone.replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        return "+233" + phone[1:]
    if phone.startswith("233"):
        return "+" + phone
    if phone.startswith("+"):
        return phone
    return "+233" + phone


# ────────────────────────────────────────────────────────
# Staff ID generation
# ────────────────────────────────────────────────────────
def generate_staff_id() -> str:
    """
    Generate a unique staff ID in the format SID-XXXX.
    Retries on collision (9 000 possible values — plenty for campus security).
    """
    from .models import SecurityProfile  # late import to avoid circular

    for _ in range(50):  # safety limit
        candidate = f"SID-{random.randint(1000, 9999)}"
        if not SecurityProfile.objects.filter(staff_id=candidate).exists():
            return candidate

    raise RuntimeError("Could not generate a unique staff ID after 50 attempts")


# ────────────────────────────────────────────────────────
# Twilio SMS
# ────────────────────────────────────────────────────────
def send_staff_id_sms(phone: str, staff_id: str) -> str | None:
    """
    Send the generated staff ID to the security user's phone via Twilio.
    Returns the Twilio message SID, or None in dry-run mode.
    """
    to_number = format_phone_e164(phone)

    body = (
        f"Welcome to KNUST SafeTrack!\n\n"
        f"Your Security Staff ID is: {staff_id}\n\n"
        f"Use this ID to log in to the Security Dashboard.\n"
        f"Do not share it with anyone."
    )

    # Dry-run mode (no Twilio credentials configured)
    dry_run = getattr(settings, "TWILIO_DRY_RUN", False)
    if dry_run:
        logger.info(
            "[TWILIO DRY-RUN] Would send SMS to %s:\n%s", to_number, body
        )
        return None

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        logger.info("SMS sent to %s — SID: %s", to_number, message.sid)
        return message.sid

    except Exception as exc:
        logger.error("Failed to send SMS to %s: %s", to_number, exc)
        raise


# ────────────────────────────────────────────────────────
# Approval workflow
# ────────────────────────────────────────────────────────
def approve_user(user, approved_by=None):
    """
    Approve a pending user.
    If security → generate staff_id, create SecurityProfile, send SMS.
    """
    from .models import SecurityProfile  # late import

    user.account_status = "approved"
    user.approved_by = approved_by
    user.approved_at = timezone.now()
    user.save(update_fields=["account_status", "approved_by", "approved_at", "updated_at"])

    if user.user_role == "security":
        staff_id = generate_staff_id()
        SecurityProfile.objects.create(user=user, staff_id=staff_id)
        send_staff_id_sms(user.phone, staff_id)
        logger.info("Security user %s approved — staff_id=%s", user.email, staff_id)

    return user


def reject_user(user):
    """Reject a pending user."""
    user.account_status = "rejected"
    user.save(update_fields=["account_status", "updated_at"])
    return user


# ────────────────────────────────────────────────────────
# Password Reset with 6-digit code
# ────────────────────────────────────────────────────────
def generate_reset_code():
    """Generate a random 6-digit code."""
    return str(random.randint(100000, 999999))


def send_reset_code_email(user):
    """
    Generate a 6-digit reset code, save it, and email it to the user.
    Invalidates any previous unused codes for the same user.
    """
    from .models import PasswordResetCode
    from django.core.mail import send_mail
    from datetime import timedelta

    # Invalidate old codes
    PasswordResetCode.objects.filter(
        user=user, is_used=False
    ).update(is_used=True)

    # Generate new code
    code = generate_reset_code()
    expires_at = timezone.now() + timedelta(minutes=15)

    PasswordResetCode.objects.create(
        user=user,
        code=code,
        email=user.email,
        expires_at=expires_at,
    )

    # Send email
    subject = "KNUST SafeTrack — Password Reset Code"
    message = (
        f"Hello {user.full_name},\n\n"
        f"Your password reset code is:\n\n"
        f"    {code}\n\n"
        f"This code expires in 15 minutes.\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— KNUST SafeTrack Team"
    )
    html_message = (
        f"<div style='font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;'>"
        f"<div style='background: #D4A017; padding: 20px; text-align: center; border-radius: 12px 12px 0 0;'>"
        f"<h1 style='color: white; margin: 0; font-size: 20px;'>KNUST SafeTrack</h1>"
        f"</div>"
        f"<div style='padding: 30px; background: #ffffff; border: 1px solid #e2e8f0;'>"
        f"<p style='color: #475569;'>Hello <strong>{user.full_name}</strong>,</p>"
        f"<p style='color: #475569;'>Your password reset code is:</p>"
        f"<div style='background: #f1f5f9; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0;'>"
        f"<span style='font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #D4A017;'>{code}</span>"
        f"</div>"
        f"<p style='color: #94a3b8; font-size: 13px;'>This code expires in <strong>15 minutes</strong>.</p>"
        f"<p style='color: #94a3b8; font-size: 13px;'>If you did not request this, please ignore this email.</p>"
        f"</div>"
        f"<div style='padding: 15px; text-align: center; background: #f8fafc; border-radius: 0 0 12px 12px; border: 1px solid #e2e8f0; border-top: none;'>"
        f"<p style='color: #94a3b8; font-size: 11px; margin: 0;'>KNUST SafeTrack — Campus Safety & Security</p>"
        f"</div>"
        f"</div>"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Reset code sent to %s", user.email)
        return True
    except Exception as exc:
        logger.error("Failed to send reset code to %s: %s", user.email, exc)
        raise


def verify_reset_code(email, code):
    """
    Verify a 6-digit reset code.
    Returns the user if valid, raises ValueError if not.
    """
    from .models import PasswordResetCode, User

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        raise ValueError("No account found with this email.")

    reset_code = PasswordResetCode.objects.filter(
        user=user,
        code=code,
        is_used=False,
    ).order_by("-created_at").first()

    if not reset_code:
        raise ValueError("Invalid reset code.")

    if reset_code.is_expired:
        raise ValueError("This code has expired. Please request a new one.")

    return user, reset_code


def reset_password_with_code(email, code, new_password):
    """
    Verify the code and set the new password.
    """
    user, reset_code = verify_reset_code(email, code)

    user.set_password(new_password)
    user.save(update_fields=["password"])

    # Mark code as used
    reset_code.is_used = True
    reset_code.save(update_fields=["is_used"])

    # Invalidate all other codes for this user
    from .models import PasswordResetCode
    PasswordResetCode.objects.filter(
        user=user, is_used=False
    ).update(is_used=True)

    logger.info("Password reset successful for %s", user.email)
    return user