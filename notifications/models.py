from django.db import models
from django.conf import settings

from common.models import TimeStampedUUIDModel


class Notification(TimeStampedUUIDModel):
    """
    Personal notification for a single user.
    Created by the system when events happen (SOS, walk, approval, etc.).
    """

    class NotificationType(models.TextChoices):
        SOS = "sos", "SOS Alert"
        CHAT = "chat", "Chat Message"
        WALK = "walk", "Walk Update"
        SHARE = "share", "Location Share"
        APPROVAL = "approval", "Account Approval"
        SYSTEM = "system", "System"
        SECURITY = "security", "Security Notice"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra payload (IDs, links, action data)",
    )

    # ── Read state ──────────────────────────────────────
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # ── Delivery tracking ───────────────────────────────
    sent_via_push = models.BooleanField(default=False)
    sent_via_ws = models.BooleanField(default=False)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "-created_at"],
                name="idx_notif_user_read_time",
            ),
            models.Index(
                fields=["user", "notification_type"],
                name="idx_notif_user_type",
            ),
        ]

    def __str__(self):
        read = "✓" if self.is_read else "●"
        return f"{read} {self.title} → {self.user.full_name}"


class BroadcastAlert(TimeStampedUUIDModel):
    """
    Campus-wide safety notice or announcement.
    Visible to all users (or filtered by role).
    Used by the Alerts page in the student app.
    """

    class AlertType(models.TextChoices):
        NOTICE = "notice", "Safety Notice"
        SHUTTLE = "shuttle", "Shuttle Update"
        SECURITY = "security", "Security Advisory"
        EMERGENCY = "emergency", "Emergency"
        MAINTENANCE = "maintenance", "Maintenance"
        GENERAL = "general", "General"

    title = models.CharField(max_length=150)
    message = models.TextField()
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        default=AlertType.NOTICE,
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Related location (e.g. 'Tech Junction')",
    )

    # ── Publishing ──────────────────────────────────────
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_alerts",
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Alert auto-hides after this time",
    )

    # ── Audience ────────────────────────────────────────
    audience = models.CharField(
        max_length=20,
        default="all",
        help_text="'all', 'student', or 'security'",
    )

    class Meta:
        db_table = "broadcast_alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["is_active", "-created_at"],
                name="idx_broadcast_active_time",
            ),
            models.Index(
                fields=["alert_type"],
                name="idx_broadcast_type",
            ),
        ]

    def __str__(self):
        active = "🟢" if self.is_active else "⚪"
        return f"{active} {self.title} ({self.get_alert_type_display()})"


class UserDevice(TimeStampedUUIDModel):
    """
    A user's device registered for push notifications.
    Stores the FCM/web push token.
    """

    class Platform(models.TextChoices):
        WEB = "web", "Web"
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    class Provider(models.TextChoices):
        FCM = "fcm", "Firebase Cloud Messaging"
        WEB_PUSH = "web_push", "Web Push"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
    )
    device_token = models.TextField(unique=True)
    push_provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
        default=Provider.FCM,
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )
    device_name = models.CharField(max_length=100, blank=True, default="")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "user_devices"
        indexes = [
            models.Index(
                fields=["user", "is_active"],
                name="idx_device_user_active",
            ),
        ]

    def __str__(self):
        return f"{self.user.full_name} — {self.platform} ({self.device_name or 'unnamed'})"


class UserPreference(models.Model):
    """
    Per-user notification preferences.
    Maps to the frontend SettingsModal toggles.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="notification_preferences",
    )

    notifications_enabled = models.BooleanField(default=True)
    sos_alerts_enabled = models.BooleanField(default=True)
    walk_updates_enabled = models.BooleanField(default=True)
    chat_notifications_enabled = models.BooleanField(default=True)
    share_location_enabled = models.BooleanField(default=True)
    sound_alerts_enabled = models.BooleanField(default=True)
    dark_mode_enabled = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preferences"

    def __str__(self):
        return f"Preferences — {self.user.full_name}"