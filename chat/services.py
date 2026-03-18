"""
Business logic for chat.
"""

import logging
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)


def get_or_create_direct_chat(user1, user2):
    from .models import Chat, ChatParticipant

    existing = Chat.objects.filter(
        chat_type="direct",
        participants__user=user1,
    ).filter(
        participants__user=user2,
    ).first()

    if existing:
        return existing, False

    chat = Chat.objects.create(
        chat_type="direct",
        created_by=user1,
    )

    ChatParticipant.objects.create(chat=chat, user=user1, participant_role="member")
    ChatParticipant.objects.create(chat=chat, user=user2, participant_role="member")

    logger.info("Direct chat created between %s and %s", user1.email, user2.email)
    return chat, True


def create_group_chat(creator, title, user_ids=None):
    """
    Create a group chat. Safe against duplicates.
    """
    from .models import Chat, ChatParticipant
    from accounts.models import User

    chat = Chat.objects.create(
        chat_type="group",
        title=title,
        created_by=creator,
    )

    # Add creator as owner — use get_or_create to be safe
    ChatParticipant.objects.get_or_create(
        chat=chat,
        user=creator,
        defaults={"participant_role": "owner"},
    )

    # Add other members — skip creator, use get_or_create
    if user_ids:
        # Remove duplicates and exclude creator
        unique_ids = set()
        for uid in user_ids:
            uid_str = str(uid)
            if uid_str != str(creator.id):
                unique_ids.add(uid)

        users = User.objects.filter(id__in=unique_ids)
        for user in users:
            ChatParticipant.objects.get_or_create(
                chat=chat,
                user=user,
                defaults={"participant_role": "member"},
            )

    logger.info("Group chat '%s' created by %s", title, creator.email)
    return chat


def create_walk_chat(walk_session):
    """
    Ensure a chat exists for a walk session.
    Safe to call multiple times — idempotent.
    """
    from .models import Chat, ChatParticipant

    title = walk_session.title or f"Walk to {walk_session.destination_name}"

    # Find or create the chat
    chat, created = Chat.objects.get_or_create(
        related_walk_session=walk_session,
        defaults={
            "chat_type": "walk_group",
            "title": title,
            "created_by": walk_session.created_by,
        },
    )

    # Sync all joined walk participants into the chat
    walk_participants = walk_session.participants.filter(
        participant_status="joined",
    ).select_related("user")

    for wp in walk_participants:
        role = "owner" if wp.participant_role == "creator" else "member"
        ChatParticipant.objects.get_or_create(
            chat=chat,
            user=wp.user,
            defaults={"participant_role": role},
        )

    if created:
        send_message(
            chat=chat,
            sender=None,
            message_text=f"Walk group chat created. Destination: {walk_session.destination_name}",
            message_type="system",
        )

    logger.info("Walk chat ensured for walk %s", walk_session.id)
    return chat


def create_sos_support_chat(sos_alert, security_user):
    from .models import Chat, ChatParticipant

    existing = Chat.objects.filter(
        related_sos_alert=sos_alert,
        chat_type="security_support",
    ).first()

    if existing:
        ChatParticipant.objects.get_or_create(
            chat=existing,
            user=security_user,
            defaults={"participant_role": "admin"},
        )
        return existing

    chat = Chat.objects.create(
        chat_type="security_support",
        title=f"SOS Support — {sos_alert.alert_code}",
        created_by=security_user,
        related_sos_alert=sos_alert,
    )

    ChatParticipant.objects.get_or_create(
        chat=chat, user=sos_alert.user,
        defaults={"participant_role": "member"},
    )
    ChatParticipant.objects.get_or_create(
        chat=chat, user=security_user,
        defaults={"participant_role": "admin"},
    )

    send_message(
        chat=chat,
        sender=None,
        message_text=f"Security support chat opened for {sos_alert.alert_code}. Help is on the way.",
        message_type="system",
    )

    logger.info("SOS support chat created for %s", sos_alert.alert_code)
    return chat


def send_message(chat, sender, message_text, message_type="text", metadata=None):
    from .models import ChatMessage

    message = ChatMessage.objects.create(
        chat=chat,
        sender=sender,
        message_type=message_type,
        message_text=message_text,
        metadata=metadata or {},
    )

    chat.save(update_fields=["updated_at"])
    return message


def mark_chat_read(chat, user):
    from .models import ChatParticipant

    now = timezone.now()
    updated = ChatParticipant.objects.filter(
        chat=chat, user=user,
    ).update(last_read_at=now)
    return updated > 0


def get_user_chats(user):
    from .models import Chat, ChatParticipant

    chat_ids = ChatParticipant.objects.filter(
        user=user,
    ).values_list("chat_id", flat=True)

    chats = Chat.objects.filter(
        id__in=chat_ids,
    ).prefetch_related(
        "participants__user",
    ).order_by("-updated_at")

    return chats


def get_total_unread_count(user):
    from .models import ChatParticipant

    participants = ChatParticipant.objects.filter(
        user=user, is_muted=False,
    ).select_related("chat")

    total = 0
    for p in participants:
        total += p.unread_count
    return total


def add_participant(chat, user, role="member"):
    from .models import ChatParticipant

    participant, created = ChatParticipant.objects.get_or_create(
        chat=chat, user=user,
        defaults={"participant_role": role},
    )

    if created:
        send_message(
            chat=chat, sender=None,
            message_text=f"{user.full_name} joined the chat.",
            message_type="system",
        )

    return participant, created


def remove_participant(chat, user):
    from .models import ChatParticipant

    deleted, _ = ChatParticipant.objects.filter(
        chat=chat, user=user,
    ).delete()

    if deleted:
        send_message(
            chat=chat, sender=None,
            message_text=f"{user.full_name} left the chat.",
            message_type="system",
        )

    return deleted > 0