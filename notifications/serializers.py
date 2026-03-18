from rest_framework import serializers
from .models import Notification, BroadcastAlert, UserDevice, UserPreference


# ────────────────────────────────────────────────────────
# Personal Notifications
# ────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    """
    Personal notification for the user.
    Matches what the frontend needs.
    """

    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "data",
            "is_read",
            "read_at",
            "time_ago",
            "created_at",
        ]

    def get_time_ago(self, obj):
        from django.utils import timezone
        diff = timezone.now() - obj.created_at
        minutes = int(diff.total_seconds() / 60)

        if minutes < 1:
            return "Just now"
        if minutes < 60:
            return f"{minutes} min ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"


# ────────────────────────────────────────────────────────
# Broadcast Alerts
# ────────────────────────────────────────────────────────

class BroadcastAlertSerializer(serializers.ModelSerializer):
    """
    Campus-wide alert / safety notice.
    Matches what the frontend Alerts page expects.
    """

    published_by_name = serializers.SerializerMethodField()
    type = serializers.CharField(source="alert_type")

    class Meta:
        model = BroadcastAlert
        fields = [
            "id",
            "title",
            "message",
            "type",
            "location",
            "published_by_name",
            "audience",
            "is_active",
            "expires_at",
            "created_at",
        ]

    def get_published_by_name(self, obj):
        if obj.published_by:
            return obj.published_by.full_name
        return "System"


class CreateBroadcastAlertSerializer(serializers.Serializer):
    """Admin creates a broadcast alert."""

    title = serializers.CharField(max_length=150)
    message = serializers.CharField()
    alert_type = serializers.ChoiceField(
        choices=BroadcastAlert.AlertType.choices,
        default="notice",
    )
    location = serializers.CharField(max_length=200, required=False, default="")
    audience = serializers.ChoiceField(
        choices=["all", "student", "security"],
        default="all",
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


# ────────────────────────────────────────────────────────
# Device Registration
# ────────────────────────────────────────────────────────

class RegisterDeviceSerializer(serializers.Serializer):
    """Register a device for push notifications."""

    device_token = serializers.CharField()
    platform = serializers.ChoiceField(choices=UserDevice.Platform.choices)
    push_provider = serializers.ChoiceField(
        choices=UserDevice.Provider.choices,
        default="fcm",
        required=False,
    )
    device_name = serializers.CharField(max_length=100, required=False, default="")


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            "id",
            "device_token",
            "platform",
            "push_provider",
            "device_name",
            "is_active",
            "last_seen_at",
            "created_at",
        ]


# ────────────────────────────────────────────────────────
# User Preferences
# ────────────────────────────────────────────────────────

class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    Maps to the frontend SettingsModal toggles.
    """

    class Meta:
        model = UserPreference
        fields = [
            "notifications_enabled",
            "sos_alerts_enabled",
            "walk_updates_enabled",
            "chat_notifications_enabled",
            "share_location_enabled",
            "sound_alerts_enabled",
            "dark_mode_enabled",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]