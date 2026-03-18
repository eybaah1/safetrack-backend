from django.db import models
from django.conf import settings

from common.models import TimeStampedUUIDModel


class Chat(TimeStampedUUIDModel):
    """
    A conversation — can be direct (2 people), group, walk-related,
    or security support.
    """

    class ChatType(models.TextChoices):
        DIRECT = "direct", "Direct Message"
        GROUP = "group", "Group Chat"
        WALK_GROUP = "walk_group", "Walk Group Chat"
        SECURITY_SUPPORT = "security_support", "Security Support"

    chat_type = models.CharField(
        max_length=20,
        choices=ChatType.choices,
    )
    title = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Display name for group/walk chats",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_chats",
    )

    # Link to walk session or SOS alert if applicable
    related_walk_session = models.ForeignKey(
        "walks.WalkSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chats",
    )
    related_sos_alert = models.ForeignKey(
        "sos.SOSAlert",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chats",
    )

    class Meta:
        db_table = "chats"
        ordering = ["-updated_at"]

    def __str__(self):
        if self.title:
            return self.title
        return f"{self.get_chat_type_display()} ({self.id})"

    @property
    def participant_count(self):
        return self.participants.count()

    @property
    def last_message(self):
        return self.messages.order_by("-sent_at").first()


class ChatParticipant(TimeStampedUUIDModel):
    """
    A user in a chat.
    Tracks when they last read messages (for unread counts).
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_participations",
    )
    participant_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        db_table = "chat_participants"
        constraints = [
            models.UniqueConstraint(
                fields=["chat", "user"],
                name="uq_chat_participant",
            ),
        ]

    def __str__(self):
        return f"{self.user.full_name} in {self.chat}"

    @property
    def unread_count(self):
        """Number of messages sent after last_read_at."""
        queryset = self.chat.messages.filter(is_deleted=False)
        if self.last_read_at:
            queryset = queryset.filter(sent_at__gt=self.last_read_at)
        # Exclude own messages
        queryset = queryset.exclude(sender=self.user)
        return queryset.count()


class ChatMessage(TimeStampedUUIDModel):
    """
    A single message in a chat.
    """

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        LOCATION = "location", "Location"
        SYSTEM = "system", "System Message"

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    message_text = models.TextField(blank=True, default="")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra data (image URL, location coords, etc.)",
    )

    sent_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "chat_messages"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(
                fields=["chat", "-sent_at"],
                name="idx_msg_chat_time",
            ),
            models.Index(
                fields=["sender", "-sent_at"],
                name="idx_msg_sender_time",
            ),
        ]

    def __str__(self):
        sender_name = self.sender.full_name if self.sender else "System"
        preview = self.message_text[:40] if self.message_text else "[media]"
        return f"{sender_name}: {preview}"