import logging
import random

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────
# Phone formatting
# ────────────────────────────────────────────────────────
def format_phone_e164(phone: str) -> str:
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
    from .models import SecurityProfile

    for _ in range(50):
        candidate = f"SID-{random.randint(1000, 9999)}"
        if not SecurityProfile.objects.filter(staff_id=candidate).exists():
            return candidate

    raise RuntimeError("Could not generate a unique staff ID after 50 attempts")


# ────────────────────────────────────────────────────────
# Send Staff ID via EMAIL
# ────────────────────────────────────────────────────────
def send_staff_id_email(user, staff_id: str) -> bool:
    """
    Send the generated staff ID to the user's email.

    NO background thread — Brevo HTTP API is fast (< 1 second).
    Removing threading eliminates the daemon-thread-killed-on-Railway
    problem and makes errors visible immediately.
    """
    # ← FIX: Capture values safely in case user object has issues
    email_address = user.email
    full_name = user.full_name or "User"  # ← FIX: handle None

    logger.info(
        "Attempting to send Staff ID email to %s (SID: %s)",
        email_address, staff_id,
    )  # ← FIX: log BEFORE sending so we know we reached this point

    subject = "KNUST SafeTrack — Your Security Staff ID"

    plain_message = (
        f"Hello {full_name},\n\n"
        f"Great news! Your security account has been APPROVED.\n\n"
        f"Your Staff ID (SID): {staff_id}\n\n"
        f"How to log in:\n"
        f"  1. Go to the Security Login page\n"
        f"  2. Enter your Staff ID: {staff_id}\n"
        f"  3. Enter your password\n\n"
        f"Keep this ID confidential. Do not share it with anyone.\n\n"
        f"— KNUST SafeTrack Team"
    )

    html_message = (
        "<div style='font-family:Arial,sans-serif;max-width:480px;margin:0 auto;'>"
        "<div style='background:#D4A017;padding:20px;text-align:center;"
        "border-radius:12px 12px 0 0;'>"
        "<h1 style='color:white;margin:0;font-size:20px;'>KNUST SafeTrack</h1>"
        "</div>"
        "<div style='padding:30px;background:#ffffff;border:1px solid #e2e8f0;'>"
        f"<p style='color:#475569;'>Hello <strong>{full_name}</strong>,</p>"
        "<p style='color:#475569;'>Great news! Your security account has been "
        "<strong style='color:#228B22;'>approved</strong>.</p>"
        "<div style='background:#f1f5f9;border-radius:12px;padding:20px;"
        "text-align:center;margin:20px 0;'>"
        "<p style='color:#475569;margin:0 0 8px;font-size:14px;'>Your Staff ID (SID):</p>"
        f"<span style='font-size:32px;font-weight:bold;letter-spacing:6px;"
        f"color:#D4A017;'>{staff_id}</span>"
        "</div>"
        "<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;"
        "padding:16px;margin:16px 0;'>"
        "<p style='color:#166534;font-size:14px;font-weight:600;margin:0 0 8px;'>"
        "How to log in:</p>"
        "<ol style='color:#166534;font-size:13px;margin:0;padding-left:20px;'>"
        f"<li>Go to the Security Login page</li>"
        f"<li>Enter your Staff ID: <strong>{staff_id}</strong></li>"
        f"<li>Enter your password</li>"
        "</ol>"
        "</div>"
        "<p style='color:#DC2626;font-size:13px;font-weight:500;'>"
        "&#128274; Keep this ID confidential. Do not share it with anyone.</p>"
        "</div>"
        "<div style='padding:15px;text-align:center;background:#f8fafc;"
        "border-radius:0 0 12px 12px;border:1px solid #e2e8f0;border-top:none;'>"
        "<p style='color:#94a3b8;font-size:11px;margin:0;'>"
        "KNUST SafeTrack &mdash; Campus Safety &amp; Security</p>"
        "</div></div>"
    )

    # ← FIX: NO threading — Brevo HTTP API is fast, threading caused silent failures
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_address],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(
            "✅ Staff ID email SENT to %s — SID: %s",
            email_address, staff_id,
        )
        return True
    except Exception as exc:
        # ← FIX: Log the FULL exception so you can see it in Railway logs
        logger.error(
            "❌ Failed to send Staff ID email to %s: %s",
            email_address, exc,
            exc_info=True,  # ← FIX: includes full traceback in logs
        )
        return False


# ────────────────────────────────────────────────────────
# Approval workflow
# ────────────────────────────────────────────────────────
def approve_user(user, approved_by=None):
    """
    Approve a pending user.
    If security → generate staff_id, create SecurityProfile, send EMAIL.
    """
    from .models import SecurityProfile

    # ← FIX: Log what we're working with
    logger.info(
        "approve_user called: email=%s, role='%s', status='%s'",
        user.email, user.user_role, user.account_status,
    )

    user.account_status = "approved"
    user.approved_by = approved_by
    user.approved_at = timezone.now()
    user.save(update_fields=["account_status", "approved_by", "approved_at", "updated_at"])

    # ← FIX: Case-insensitive comparison
    if user.user_role and user.user_role.strip().lower() == "security":

        # ← FIX: Handle the case where SecurityProfile already exists
        #   (from a previous failed approval attempt)
        profile = SecurityProfile.objects.filter(user=user).first()

        if profile:
            # Profile exists from a previous attempt — reuse the staff_id
            staff_id = profile.staff_id
            logger.warning(
                "SecurityProfile already exists for %s — "
                "reusing staff_id=%s, resending email",
                user.email, staff_id,
            )
        else:
            # Create new profile
            staff_id = generate_staff_id()
            try:
                SecurityProfile.objects.create(user=user, staff_id=staff_id)
                logger.info(
                    "SecurityProfile created for %s — staff_id=%s",
                    user.email, staff_id,
                )
            except IntegrityError as exc:
                logger.error(
                    "IntegrityError creating SecurityProfile for %s: %s",
                    user.email, exc,
                )
                raise

        # ← FIX: Send email synchronously so errors are visible
        email_sent = send_staff_id_email(user, staff_id)

        if email_sent:
            logger.info(
                "✅ Security user %s fully approved — staff_id=%s, email sent",
                user.email, staff_id,
            )
        else:
            logger.error(
                "⚠️ Security user %s approved but email FAILED — staff_id=%s",
                user.email, staff_id,
            )
    else:
        # ← FIX: Log when the security branch is NOT entered
        logger.info(
            "User %s approved (role='%s' — not security, no staff ID needed)",
            user.email, user.user_role,
        )

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
    return str(random.randint(100000, 999999))


def send_reset_code_email(user):
    """
    Generate a 6-digit reset code, save it, and email it.
    """
    from .models import PasswordResetCode
    from datetime import timedelta

    # Invalidate old codes
    PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

    code = generate_reset_code()
    expires_at = timezone.now() + timedelta(minutes=15)

    PasswordResetCode.objects.create(
        user=user,
        code=code,
        email=user.email,
        expires_at=expires_at,
    )

    full_name = user.full_name or "User"

    subject = "KNUST SafeTrack — Password Reset Code"

    message = (
        f"Hello {full_name},\n\n"
        f"Your password reset code is:\n\n"
        f"    {code}\n\n"
        f"This code expires in 15 minutes.\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— KNUST SafeTrack Team"
    )

    html_message = (
        "<div style='font-family:Arial,sans-serif;max-width:480px;margin:0 auto;'>"
        "<div style='background:#D4A017;padding:20px;text-align:center;"
        "border-radius:12px 12px 0 0;'>"
        "<h1 style='color:white;margin:0;font-size:20px;'>KNUST SafeTrack</h1>"
        "</div>"
        "<div style='padding:30px;background:#ffffff;border:1px solid #e2e8f0;'>"
        f"<p style='color:#475569;'>Hello <strong>{full_name}</strong>,</p>"
        "<p style='color:#475569;'>Your password reset code is:</p>"
        "<div style='background:#f1f5f9;border-radius:12px;padding:20px;"
        "text-align:center;margin:20px 0;'>"
        f"<span style='font-size:32px;font-weight:bold;letter-spacing:8px;"
        f"color:#D4A017;'>{code}</span>"
        "</div>"
        "<p style='color:#94a3b8;font-size:13px;'>This code expires in "
        "<strong>15 minutes</strong>.</p>"
        "<p style='color:#94a3b8;font-size:13px;'>If you did not request this, "
        "please ignore this email.</p>"
        "</div>"
        "<div style='padding:15px;text-align:center;background:#f8fafc;"
        "border-radius:0 0 12px 12px;border:1px solid #e2e8f0;border-top:none;'>"
        "<p style='color:#94a3b8;font-size:11px;margin:0;'>"
        "KNUST SafeTrack &mdash; Campus Safety &amp; Security</p>"
        "</div></div>"
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
        logger.error(
            "Failed to send reset code to %s: %s",
            user.email, exc, exc_info=True,
        )
        raise


def verify_reset_code(email, code):
    from .models import PasswordResetCode, User

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        raise ValueError("No account found with this email.")

    reset_code = PasswordResetCode.objects.filter(
        user=user, code=code, is_used=False,
    ).order_by("-created_at").first()

    if not reset_code:
        raise ValueError("Invalid reset code.")

    if reset_code.is_expired:
        raise ValueError("This code has expired. Please request a new one.")

    return user, reset_code


def reset_password_with_code(email, code, new_password):
    user, reset_code = verify_reset_code(email, code)

    user.set_password(new_password)
    user.save(update_fields=["password"])

    reset_code.is_used = True
    reset_code.save(update_fields=["is_used"])

    from .models import PasswordResetCode
    PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

    logger.info("Password reset successful for %s", user.email)
    return user