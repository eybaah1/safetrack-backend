from rest_framework import serializers
from .models import Chat, ChatParticipant, ChatMessage


# ────────────────────────────────────────────────────────
# Messages
# ────────────────────────────────────────────────────────
class ChatMessageSerializer(serializers.ModelSerializer):
    """Full message serializer."""

    sender_id = serializers.UUIDField(source="sender.id", read_only=True, allow_null=True)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "sender_id",
            "sender_name",
            "message_type",
            "message_text",
            "metadata",
            "sent_at",
            "edited_at",
            "is_deleted",
        ]

    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.full_name
        return "System"


class SendMessageSerializer(serializers.Serializer):
    """POST body for sending a message via REST API."""

    message_text = serializers.CharField(min_length=1, max_length=5000)
    message_type = serializers.ChoiceField(
        choices=ChatMessage.MessageType.choices,
        default="text",
        required=False,
    )
    metadata = serializers.JSONField(required=False, default=dict)


# ────────────────────────────────────────────────────────
# Participants
# ────────────────────────────────────────────────────────
class ChatParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField(source="user.full_name")
    avatar = serializers.SerializerMethodField()
    unread = serializers.IntegerField(source="unread_count", read_only=True)

    class Meta:
        model = ChatParticipant
        fields = [
            "id",
            "user_id",
            "name",
            "avatar",
            "participant_role",
            "is_muted",
            "last_read_at",
            "unread",
            "joined_at",
        ]

    def get_avatar(self, obj):
        """Generate initials for avatar."""
        name = obj.user.full_name
        parts = name.split()
        if len(parts) >= 2:
            return parts[0][0].upper() + parts[1][0].upper()
        return name[:2].upper()


# ────────────────────────────────────────────────────────
# Chats (conversation list)
# ────────────────────────────────────────────────────────
class ChatListSerializer(serializers.ModelSerializer):
    """
    For the conversation list view.
    Matches what the frontend Chat component expects.
    """

    last_message = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    is_group = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "display_name",
            "subtitle",
            "avatar",
            "is_group",
            "last_message",
            "last_message_time",
            "unread_count",
            "other_user",
            "updated_at",
        ]

    def _get_current_user(self):
        return self.context.get("request").user

    def get_display_name(self, obj):
        if obj.title:
            return obj.title
        if obj.chat_type == "direct":
            other = self._get_other_participant(obj)
            if other:
                return other.user.full_name
        return f"Chat ({obj.chat_type})"

    def get_subtitle(self, obj):
        if obj.chat_type == "direct":
            other = self._get_other_participant(obj)
            if other:
                return other.user.hostel_name
            return ""
        count = obj.participants.count()
        return f"Group • {count} members"

    def get_avatar(self, obj):
        if obj.chat_type == "direct":
            other = self._get_other_participant(obj)
            if other:
                name = other.user.full_name
                parts = name.split()
                if len(parts) >= 2:
                    return parts[0][0].upper() + parts[1][0].upper()
                return name[:2].upper()
        if obj.title:
            return obj.title[:2].upper()
        return "GC"

    def get_is_group(self, obj):
        return obj.chat_type != "direct"

    def get_last_message(self, obj):
        msg = obj.last_message
        if not msg:
            return ""
        if msg.is_deleted:
            return "Message deleted"
        prefix = ""
        if msg.sender and obj.chat_type != "direct":
            first_name = msg.sender.full_name.split()[0]
            prefix = f"{first_name}: "
        return f"{prefix}{msg.message_text}"

    def get_last_message_time(self, obj):
        msg = obj.last_message
        if not msg:
            return None
        return msg.sent_at.isoformat()

    def get_unread_count(self, obj):
        user = self._get_current_user()
        try:
            participant = obj.participants.get(user=user)
            return participant.unread_count
        except Exception:
            return 0

    def get_other_user(self, obj):
        if obj.chat_type != "direct":
            return None
        other = self._get_other_participant(obj)
        if other:
            return {
                "id": str(other.user.id),
                "name": other.user.full_name,
                "hostel": other.user.hostel_name,
            }
        return None

    def _get_other_participant(self, obj):
        user = self._get_current_user()
        return obj.participants.exclude(user=user).select_related("user").first()


class ChatDetailSerializer(serializers.ModelSerializer):
    """Full chat detail with participants."""

    participants = ChatParticipantSerializer(many=True, read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "chat_type",
            "title",
            "display_name",
            "related_walk_session_id",
            "related_sos_alert_id",
            "participants",
            "created_at",
            "updated_at",
        ]

    def get_display_name(self, obj):
        if obj.title:
            return obj.title
        if obj.chat_type == "direct":
            user = self.context.get("request").user
            other = obj.participants.exclude(user=user).select_related("user").first()
            if other:
                return other.user.full_name
        return f"Chat ({obj.chat_type})"


class CreateDirectChatSerializer(serializers.Serializer):
    """Create or get a direct chat."""
    user_id = serializers.UUIDField()


class CreateGroupChatSerializer(serializers.Serializer):
    """Create a group chat."""
    title = serializers.CharField(max_length=150)
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50,
    )


class AddParticipantSerializer(serializers.Serializer):
    """Add a user to a chat."""
    user_id = serializers.UUIDField()