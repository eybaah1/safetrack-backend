from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminOrSecurity
from .models import Chat, ChatParticipant, ChatMessage
from .serializers import (
    ChatListSerializer,
    ChatDetailSerializer,
    ChatMessageSerializer,
    SendMessageSerializer,
    ChatParticipantSerializer,
    CreateDirectChatSerializer,
    CreateGroupChatSerializer,
    AddParticipantSerializer,
)
from .services import (
    get_or_create_direct_chat,
    create_group_chat,
    create_sos_support_chat,
    send_message,
    mark_chat_read,
    get_user_chats,
    get_total_unread_count,
    add_participant,
    remove_participant,
)
from .filters import ChatMessageFilter


# ════════════════════════════════════════════════════════
# CONVERSATION LIST
# ════════════════════════════════════════════════════════

class ChatListView(generics.ListAPIView):
    """
    GET /api/v1/chats/

    List all chats the current user is in.
    Ordered by most recent activity.
    Includes last message preview and unread count.
    """

    serializer_class = ChatListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return get_user_chats(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class UnreadCountView(APIView):
    """
    GET /api/v1/chats/unread/

    Total unread count across all chats.
    Used for the chat tab badge number.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = get_total_unread_count(request.user)
        return Response({"unread_count": count})


# ════════════════════════════════════════════════════════
# CREATE CHATS
# ════════════════════════════════════════════════════════

class CreateDirectChatView(APIView):
    """
    POST /api/v1/chats/direct/

    Create or get a direct chat with another user.
    Body: { "user_id": "<uuid>" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from accounts.models import User

        serializer = CreateDirectChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            other_user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if other_user == request.user:
            return Response(
                {"error": "Cannot create a chat with yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chat, created = get_or_create_direct_chat(request.user, other_user)

        return Response(
            {
                "message": "Chat ready." if not created else "Chat created.",
                "chat": ChatDetailSerializer(chat, context={"request": request}).data,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CreateGroupChatView(APIView):
    """
    POST /api/v1/chats/group/

    Create a new group chat.
    Body: { "title": "Chat Name", "user_ids": ["uuid1", "uuid2"] }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateGroupChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat = create_group_chat(
            creator=request.user,
            title=serializer.validated_data["title"],
            user_ids=serializer.validated_data["user_ids"],
        )

        return Response(
            {
                "message": "Group chat created.",
                "chat": ChatDetailSerializer(chat, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CreateSOSSupportChatView(APIView):
    """
    POST /api/v1/chats/sos-support/

    Create a support chat for an SOS alert.
    Body: { "sos_alert_id": "<uuid>" }
    Security/admin only.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def post(self, request):
        from sos.models import SOSAlert

        sos_id = request.data.get("sos_alert_id")
        if not sos_id:
            return Response(
                {"error": "sos_alert_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sos_alert = SOSAlert.objects.get(id=sos_id)
        except SOSAlert.DoesNotExist:
            return Response(
                {"error": "SOS alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        chat = create_sos_support_chat(sos_alert, request.user)

        return Response(
            {
                "message": "SOS support chat ready.",
                "chat": ChatDetailSerializer(chat, context={"request": request}).data,
            },
        )


# ════════════════════════════════════════════════════════
# CHAT DETAIL & MESSAGES
# ════════════════════════════════════════════════════════

class ChatDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/chats/<id>/

    Chat detail with participants.
    """

    serializer_class = ChatDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return Chat.objects.filter(
            participants__user=self.request.user,
        ).prefetch_related("participants__user")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class ChatMessagesView(generics.ListAPIView):
    """
    GET  /api/v1/chats/<id>/messages/   → message history
    POST /api/v1/chats/<id>/messages/   → send message
    """

    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ChatMessageFilter

    def get_queryset(self):
        chat_id = self.kwargs["id"]

        is_participant = ChatParticipant.objects.filter(
            chat_id=chat_id,
            user=self.request.user,
        ).exists()

        if not is_participant:
            return ChatMessage.objects.none()

        return ChatMessage.objects.filter(
            chat_id=chat_id,
            is_deleted=False,
        ).select_related("sender").order_by("-sent_at")

    def post(self, request, id):
        # Verify user is a participant
        is_participant = ChatParticipant.objects.filter(
            chat_id=id,
            user=request.user,
        ).exists()

        if not is_participant:
            return Response(
                {"error": "You are not in this chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            chat = Chat.objects.get(id=id)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        message = send_message(
            chat=chat,
            sender=request.user,
            message_text=serializer.validated_data["message_text"],
            message_type=serializer.validated_data.get("message_type", "text"),
            metadata=serializer.validated_data.get("metadata", {}),
        )

        # Broadcast via WebSocket if available
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                room_group = f"chat_{chat.id}"
                async_to_sync(channel_layer.group_send)(
                    room_group,
                    {
                        "type": "chat_message",
                        "message": {
                            "id": str(message.id),
                            "sender_id": str(message.sender.id) if message.sender else None,
                            "sender_name": message.sender.full_name if message.sender else "System",
                            "text": message.message_text,
                            "message_type": message.message_type,
                            "metadata": message.metadata,
                            "time": message.sent_at.isoformat(),
                        },
                    },
                )
        except Exception:
            pass

        return Response(
            {
                "message": "Sent.",
                "data": ChatMessageSerializer(message).data,
            },
            status=status.HTTP_201_CREATED,
        )
    """
    GET /api/v1/chats/<id>/messages/

    Message history for a chat.
    Ordered newest first. Supports pagination.
    """

    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ChatMessageFilter

    def get_queryset(self):
        chat_id = self.kwargs["id"]

        # Verify user is a participant
        is_participant = ChatParticipant.objects.filter(
            chat_id=chat_id,
            user=self.request.user,
        ).exists()

        if not is_participant:
            return ChatMessage.objects.none()

        return ChatMessage.objects.filter(
            chat_id=chat_id,
            is_deleted=False,
        ).select_related("sender").order_by("-sent_at")


class SendMessageView(APIView):
    """
    POST /api/v1/chats/<id>/messages/

    Send a message via REST API.
    For clients that don't use WebSocket.
    Also broadcasts via WebSocket to connected clients.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        # Verify user is a participant
        is_participant = ChatParticipant.objects.filter(
            chat_id=id,
            user=request.user,
        ).exists()

        if not is_participant:
            return Response(
                {"error": "You are not in this chat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            chat = Chat.objects.get(id=id)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        message = send_message(
            chat=chat,
            sender=request.user,
            message_text=serializer.validated_data["message_text"],
            message_type=serializer.validated_data.get("message_type", "text"),
            metadata=serializer.validated_data.get("metadata", {}),
        )

        # Broadcast via WebSocket
        self._broadcast_message(chat, message)

        return Response(
            {
                "message": "Sent.",
                "data": ChatMessageSerializer(message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _broadcast_message(self, chat, message):
        """Send message to WebSocket room if Channels is available."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer:
                room_group = f"chat_{chat.id}"
                async_to_sync(channel_layer.group_send)(
                    room_group,
                    {
                        "type": "chat_message",
                        "message": {
                            "id": str(message.id),
                            "sender_id": str(message.sender.id) if message.sender else None,
                            "sender_name": message.sender.full_name if message.sender else "System",
                            "text": message.message_text,
                            "message_type": message.message_type,
                            "metadata": message.metadata,
                            "time": message.sent_at.isoformat(),
                        },
                    },
                )
        except Exception:
            pass  # WebSocket broadcast is best-effort


class MarkChatReadView(APIView):
    """
    POST /api/v1/chats/<id>/read/

    Mark all messages in a chat as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            chat = Chat.objects.get(id=id)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success = mark_chat_read(chat, request.user)

        if success:
            return Response({"message": "Chat marked as read."})
        return Response(
            {"error": "You are not in this chat."},
            status=status.HTTP_403_FORBIDDEN,
        )


# ════════════════════════════════════════════════════════
# PARTICIPANTS
# ════════════════════════════════════════════════════════

class ChatParticipantsView(APIView):
    """
    GET  /api/v1/chats/<id>/participants/     — list participants
    POST /api/v1/chats/<id>/participants/     — add participant
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            chat = Chat.objects.get(id=id)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        participants = ChatParticipant.objects.filter(
            chat=chat,
        ).select_related("user")

        serializer = ChatParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    def post(self, request, id):
        from accounts.models import User

        try:
            chat = Chat.objects.get(id=id)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only group chats allow adding participants
        if chat.chat_type == "direct":
            return Response(
                {"error": "Cannot add participants to a direct chat."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AddParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        participant, created = add_participant(chat, user)

        if created:
            return Response(
                {"message": f"{user.full_name} added to chat."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": f"{user.full_name} is already in this chat."},
        )


class LeaveChatView(APIView):
    """
    POST /api/v1/chats/<id>/leave/

    Leave a group chat.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            chat = Chat.objects.get(id=id)
        except Chat.DoesNotExist:
            return Response(
                {"error": "Chat not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if chat.chat_type == "direct":
            return Response(
                {"error": "Cannot leave a direct chat."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success = remove_participant(chat, request.user)

        if success:
            return Response({"message": "You left the chat."})
        return Response(
            {"error": "You are not in this chat."},
            status=status.HTTP_400_BAD_REQUEST,
        )