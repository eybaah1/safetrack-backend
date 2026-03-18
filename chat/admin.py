from django.contrib import admin
from .models import Chat, ChatParticipant, ChatMessage


class ChatParticipantInline(admin.TabularInline):
    model = ChatParticipant
    extra = 0
    raw_id_fields = ["user"]
    readonly_fields = ["joined_at"]


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    raw_id_fields = ["sender"]
    readonly_fields = ["sent_at"]
    ordering = ["-sent_at"]
    max_num = 20  # Don't load all messages


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = [
        "title_display",
        "chat_type",
        "participant_count",
        "created_by",
        "updated_at",
    ]
    list_filter = ["chat_type", "created_at"]
    search_fields = ["title", "created_by__full_name"]
    ordering = ["-updated_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["created_by", "related_walk_session", "related_sos_alert"]
    inlines = [ChatParticipantInline]

    @admin.display(description="Chat")
    def title_display(self, obj):
        return obj.title or f"{obj.get_chat_type_display()} ({str(obj.id)[:8]})"


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    list_display = ["user", "chat", "participant_role", "is_muted", "last_read_at", "joined_at"]
    list_filter = ["participant_role", "is_muted"]
    search_fields = ["user__full_name", "chat__title"]
    raw_id_fields = ["user", "chat"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["short_text", "sender", "chat", "message_type", "sent_at", "is_deleted"]
    list_filter = ["message_type", "is_deleted", "sent_at"]
    search_fields = ["message_text", "sender__full_name"]
    ordering = ["-sent_at"]
    readonly_fields = ["id", "sent_at", "created_at", "updated_at"]
    raw_id_fields = ["sender", "chat"]
    list_per_page = 50

    @admin.display(description="Message")
    def short_text(self, obj):
        if obj.is_deleted:
            return "[deleted]"
        return obj.message_text[:60] if obj.message_text else "[media]"