import django_filters
from .models import ChatMessage


class ChatMessageFilter(django_filters.FilterSet):
    message_type = django_filters.ChoiceFilter(
        choices=ChatMessage.MessageType.choices,
    )
    sent_after = django_filters.DateTimeFilter(
        field_name="sent_at",
        lookup_expr="gte",
    )
    sent_before = django_filters.DateTimeFilter(
        field_name="sent_at",
        lookup_expr="lte",
    )

    class Meta:
        model = ChatMessage
        fields = ["message_type"]