from django.urls import path
from . import views

urlpatterns = [
    # ── Conversation list ───────────────────────────────
    path(
        "",
        views.ChatListView.as_view(),
        name="chat-list",
    ),
    path(
        "unread/",
        views.UnreadCountView.as_view(),
        name="chat-unread",
    ),

    # ── Create chats ────────────────────────────────────
    path(
        "direct/",
        views.CreateDirectChatView.as_view(),
        name="create-direct-chat",
    ),
    path(
        "group/",
        views.CreateGroupChatView.as_view(),
        name="create-group-chat",
    ),
    path(
        "sos-support/",
        views.CreateSOSSupportChatView.as_view(),
        name="create-sos-support-chat",
    ),

    # ── Chat detail & messages ──────────────────────────
    path(
        "<uuid:id>/",
        views.ChatDetailView.as_view(),
        name="chat-detail",
    ),
    path(
        "<uuid:id>/messages/",
        views.ChatMessagesView.as_view(),
        name="chat-messages",
    ),
    path(
        "<uuid:id>/read/",
        views.MarkChatReadView.as_view(),
        name="mark-chat-read",
    ),

    # ── Participants ────────────────────────────────────
    path(
        "<uuid:id>/participants/",
        views.ChatParticipantsView.as_view(),
        name="chat-participants",
    ),
    path(
        "<uuid:id>/leave/",
        views.LeaveChatView.as_view(),
        name="leave-chat",
    ),
]