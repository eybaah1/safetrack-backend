"""
WebSocket consumer for real-time chat.
Handles connecting, sending/receiving messages, typing indicators.
"""

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for a single chat room.

    Connect: ws://localhost:8000/ws/chat/<chat_id>/?token=<jwt>
    """

    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.room_group_name = f"chat_{self.chat_id}"
        self.user = self.scope.get("user", AnonymousUser())

        # Reject if not authenticated
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Verify user is a participant in this chat
        is_participant = await self._is_participant()
        if not is_participant:
            await self.close(code=4003)
            return

        # Join the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

        # Notify others that user came online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "user_id": str(self.user.id),
                "user_name": self.user.full_name,
                "status": "online",
            },
        )

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            # Notify others that user went offline
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_status",
                    "user_id": str(self.user.id),
                    "user_name": self.user.full_name,
                    "status": "offline",
                },
            )

            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive_json(self, content):
        """
        Handle incoming WebSocket messages.

        Message types:
          { "type": "message", "text": "Hello!" }
          { "type": "typing", "is_typing": true }
          { "type": "read" }
          { "type": "location", "lat": 6.67, "lng": -1.57 }
        """
        msg_type = content.get("type", "")

        if msg_type == "message":
            await self._handle_message(content)
        elif msg_type == "typing":
            await self._handle_typing(content)
        elif msg_type == "read":
            await self._handle_read()
        elif msg_type == "location":
            await self._handle_location(content)

    # ── Message handlers ────────────────────────────────

    async def _handle_message(self, content):
        text = content.get("text", "").strip()
        if not text:
            return

        # Save to database
        message_data = await self._save_message(text)

        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_data,
            },
        )

    async def _handle_typing(self, content):
        is_typing = content.get("is_typing", False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "user_id": str(self.user.id),
                "user_name": self.user.full_name,
                "is_typing": is_typing,
            },
        )

    async def _handle_read(self):
        await self._mark_read()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "read_receipt",
                "user_id": str(self.user.id),
                "user_name": self.user.full_name,
            },
        )

    async def _handle_location(self, content):
        lat = content.get("lat")
        lng = content.get("lng")

        if lat is None or lng is None:
            return

        # Save as location message
        message_data = await self._save_location_message(lat, lng)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_data,
            },
        )

    # ── Group message handlers (called by channel layer) ──

    async def chat_message(self, event):
        """Send message to WebSocket client."""
        await self.send_json({
            "type": "message",
            "message": event["message"],
        })

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket client."""
        # Don't send to the user who is typing
        if event["user_id"] != str(self.user.id):
            await self.send_json({
                "type": "typing",
                "user_id": event["user_id"],
                "user_name": event["user_name"],
                "is_typing": event["is_typing"],
            })

    async def read_receipt(self, event):
        """Send read receipt to WebSocket client."""
        if event["user_id"] != str(self.user.id):
            await self.send_json({
                "type": "read",
                "user_id": event["user_id"],
                "user_name": event["user_name"],
            })

    async def user_status(self, event):
        """Send user online/offline status."""
        if event["user_id"] != str(self.user.id):
            await self.send_json({
                "type": "status",
                "user_id": event["user_id"],
                "user_name": event["user_name"],
                "status": event["status"],
            })

    # ── Database operations ─────────────────────────────

    @database_sync_to_async
    def _is_participant(self):
        from .models import ChatParticipant
        return ChatParticipant.objects.filter(
            chat_id=self.chat_id,
            user=self.user,
        ).exists()

    @database_sync_to_async
    def _save_message(self, text):
        from .services import send_message
        from .models import Chat

        chat = Chat.objects.get(id=self.chat_id)
        message = send_message(
            chat=chat,
            sender=self.user,
            message_text=text,
            message_type="text",
        )

        return {
            "id": str(message.id),
            "sender_id": str(self.user.id),
            "sender_name": self.user.full_name,
            "text": message.message_text,
            "message_type": "text",
            "time": message.sent_at.isoformat(),
        }

    @database_sync_to_async
    def _save_location_message(self, lat, lng):
        from .services import send_message
        from .models import Chat

        chat = Chat.objects.get(id=self.chat_id)
        message = send_message(
            chat=chat,
            sender=self.user,
            message_text="📍 Shared location",
            message_type="location",
            metadata={"lat": lat, "lng": lng},
        )

        return {
            "id": str(message.id),
            "sender_id": str(self.user.id),
            "sender_name": self.user.full_name,
            "text": message.message_text,
            "message_type": "location",
            "metadata": {"lat": lat, "lng": lng},
            "time": message.sent_at.isoformat(),
        }

    @database_sync_to_async
    def _mark_read(self):
        from .services import mark_chat_read
        from .models import Chat

        chat = Chat.objects.get(id=self.chat_id)
        mark_chat_read(chat, self.user)