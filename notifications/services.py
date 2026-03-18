"""
Business logic for creating and delivering notifications.
Other apps call these functions to notify users.
"""

import logging
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────
# CREATE PERSONAL NOTIFICATIONS
# ────────────────────────────────────────────────────────

def notify_user(user, notification_type, title, message, data=None):
    """
    Create a personal notification for a single user.
    Also attempts WebSocket delivery if Channels is available.
    """
    from .models import Notification, UserPreference

    # Check user preferences
    try:
        prefs = user.notification_preferences
        if not prefs.notifications_enabled:
            return None

        # Check type-specific preferences
        type_pref_map = {
            "sos": prefs.sos_alerts_enabled,
            "chat": prefs.chat_notifications_enabled,
            "walk": prefs.walk_updates_enabled,
        }
        if not type_pref_map.get(notification_type, True):
            return None
    except UserPreference.DoesNotExist:
        pass  # No preferences set — send anyway

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data or {},
    )

    # Try WebSocket delivery
    _send_ws_notification(user, notification)

    logger.info(
        "Notification created: [%s] %s → %s",
        notification_type,
        title,
        user.email,
    )

    return notification


def notify_users(users, notification_type, title, message, data=None):
    """
    Create notifications for multiple users.
    """
    notifications = []
    for user in users:
        notif = notify_user(user, notification_type, title, message, data)
        if notif:
            notifications.append(notif)
    return notifications


def notify_security_team(title, message, notification_type="security", data=None):
    """
    Notify all approved security users.
    Used when SOS is triggered, walks need monitoring, etc.
    """
    from accounts.models import User

    security_users = User.objects.filter(
        user_role="security",
        account_status="approved",
        is_active=True,
    )

    return notify_users(security_users, notification_type, title, message, data)


def notify_admins(title, message, notification_type="system", data=None):
    """
    Notify all admin users.
    Used for system events, pending approvals, etc.
    """
    from accounts.models import User

    admin_users = User.objects.filter(
        Q(user_role="admin") | Q(is_superuser=True),
        is_active=True,
    )

    return notify_users(admin_users, notification_type, title, message, data)


# ────────────────────────────────────────────────────────
# CONVENIENCE FUNCTIONS FOR OTHER APPS
# ────────────────────────────────────────────────────────

def notify_sos_triggered(sos_alert):
    """Called by the SOS app when an alert is triggered."""
    # Notify security team
    notify_security_team(
        title=f"🚨 SOS Alert — {sos_alert.user.full_name}",
        message=f"SOS triggered at {sos_alert.location_text or 'unknown location'}. Student needs help.",
        notification_type="sos",
        data={
            "sos_alert_id": str(sos_alert.id),
            "alert_code": sos_alert.alert_code,
            "student_name": sos_alert.user.full_name,
            "lat": sos_alert.latitude,
            "lng": sos_alert.longitude,
        },
    )

    # Notify student's emergency contacts (as in-app notification)
    try:
        contacts = sos_alert.user.emergency_contacts.filter(notify_for_sos=True)
        # In-app we just notify the student that contacts were alerted
        if contacts.exists():
            notify_user(
                user=sos_alert.user,
                notification_type="sos",
                title="Emergency contacts notified",
                message=f"Your emergency contacts have been alerted about your SOS.",
                data={"sos_alert_id": str(sos_alert.id)},
            )
    except Exception as exc:
        logger.error("Failed to process emergency contacts: %s", exc)


def notify_sos_resolved(sos_alert):
    """Called when an SOS alert is resolved."""
    notify_user(
        user=sos_alert.user,
        notification_type="sos",
        title="SOS Resolved",
        message=f"Your SOS alert ({sos_alert.alert_code}) has been resolved. Stay safe!",
        data={"sos_alert_id": str(sos_alert.id)},
    )


def notify_patrol_assigned(sos_alert, assignment):
    """Called when a patrol is assigned to an SOS."""
    notify_user(
        user=sos_alert.user,
        notification_type="security",
        title="Help is on the way!",
        message=f"{assignment.responder_name} has been dispatched to your location.",
        data={
            "sos_alert_id": str(sos_alert.id),
            "assignment_id": str(assignment.id),
        },
    )


def notify_walk_joined(walk_session, new_member):
    """Called when someone joins a walk group."""
    # Notify the creator
    if walk_session.created_by != new_member:
        notify_user(
            user=walk_session.created_by,
            notification_type="walk",
            title="New group member",
            message=f"{new_member.full_name} joined your walk to {walk_session.destination_name}.",
            data={"walk_session_id": str(walk_session.id)},
        )


def notify_walk_started(walk_session):
    """Called when a walk session starts."""
    participants = walk_session.participants.filter(
        participant_status="joined",
    ).select_related("user")

    for p in participants:
        if p.user != walk_session.created_by:
            notify_user(
                user=p.user,
                notification_type="walk",
                title="Walk started!",
                message=f"Your walk to {walk_session.destination_name} has started. Share your location.",
                data={"walk_session_id": str(walk_session.id)},
            )


def notify_account_approved(user):
    """Called when admin approves a user."""
    notify_user(
        user=user,
        notification_type="approval",
        title="Account Approved! ✅",
        message="Your SafeTrack account has been approved. You can now sign in.",
        data={"approved": True},
    )

    if user.user_role == "security":
        notify_user(
            user=user,
            notification_type="approval",
            title="Staff ID Sent",
            message="Your Staff ID has been sent to your phone via SMS. Use it to log in.",
        )


def notify_account_rejected(user):
    """Called when admin rejects a user."""
    notify_user(
        user=user,
        notification_type="approval",
        title="Account Request Update",
        message="Your SafeTrack account request was not approved. Contact admin for details.",
        data={"rejected": True},
    )


# ────────────────────────────────────────────────────────
# READ / UNREAD
# ────────────────────────────────────────────────────────

def mark_notification_read(notification):
    """Mark a single notification as read."""
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at", "updated_at"])


def mark_all_read(user):
    """Mark all of a user's notifications as read."""
    from .models import Notification

    now = timezone.now()
    count = Notification.objects.filter(
        user=user,
        is_read=False,
    ).update(is_read=True, read_at=now)

    return count


def get_unread_count(user):
    """Get total unread notification count for a user."""
    from .models import Notification

    return Notification.objects.filter(
        user=user,
        is_read=False,
    ).count()


# ────────────────────────────────────────────────────────
# BROADCAST ALERTS
# ────────────────────────────────────────────────────────

def create_broadcast_alert(published_by, title, message, alert_type="notice", **kwargs):
    """
    Create a campus-wide broadcast alert.
    """
    from .models import BroadcastAlert

    alert = BroadcastAlert.objects.create(
        title=title,
        message=message,
        alert_type=alert_type,
        published_by=published_by,
        location=kwargs.get("location", ""),
        audience=kwargs.get("audience", "all"),
        expires_at=kwargs.get("expires_at"),
    )

    logger.info(
        "Broadcast alert created: [%s] %s by %s",
        alert_type,
        title,
        published_by.email if published_by else "system",
    )

    return alert


def get_active_broadcasts(user_role="all"):
    """
    Get all currently active broadcast alerts for a given audience.
    Filters out expired alerts.
    """
    from .models import BroadcastAlert

    now = timezone.now()

    queryset = BroadcastAlert.objects.filter(
        is_active=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now),
    )

    if user_role != "all":
        queryset = queryset.filter(
            Q(audience="all") | Q(audience=user_role),
        )

    return queryset.order_by("-created_at")


# ────────────────────────────────────────────────────────
# DEVICE REGISTRATION
# ────────────────────────────────────────────────────────

def register_device(user, device_token, platform, **kwargs):
    """
    Register a device for push notifications.
    If device_token already exists, update the user association.
    """
    from .models import UserDevice

    device, created = UserDevice.objects.update_or_create(
        device_token=device_token,
        defaults={
            "user": user,
            "platform": platform,
            "push_provider": kwargs.get("push_provider", "fcm"),
            "device_name": kwargs.get("device_name", ""),
            "is_active": True,
            "last_seen_at": timezone.now(),
        },
    )

    logger.info(
        "Device %s for %s (%s)",
        "registered" if created else "updated",
        user.email,
        platform,
    )

    return device, created


def unregister_device(device_token):
    """Deactivate a device token."""
    from .models import UserDevice

    updated = UserDevice.objects.filter(
        device_token=device_token,
    ).update(is_active=False)

    return updated > 0


# ────────────────────────────────────────────────────────
# WEBSOCKET DELIVERY
# ────────────────────────────────────────────────────────

def _send_ws_notification(user, notification):
    """
    Push notification to user via WebSocket if they are connected.
    Best-effort — fails silently.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        room = f"notifications_{user.id}"
        async_to_sync(channel_layer.group_send)(
            room,
            {
                "type": "notification_message",
                "notification": {
                    "id": str(notification.id),
                    "notification_type": notification.notification_type,
                    "title": notification.title,
                    "message": notification.message,
                    "data": notification.data,
                    "created_at": notification.created_at.isoformat(),
                },
            },
        )

        notification.sent_via_ws = True
        notification.save(update_fields=["sent_via_ws"])

    except Exception:
        pass  # WebSocket delivery is best-effort