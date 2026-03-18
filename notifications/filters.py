import django_filters
from .models import Notification, BroadcastAlert


class NotificationFilter(django_filters.FilterSet):
    notification_type = django_filters.ChoiceFilter(
        choices=Notification.NotificationType.choices,
    )
    is_read = django_filters.BooleanFilter()

    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    class Meta:
        model = Notification
        fields = ["notification_type", "is_read"]


class BroadcastAlertFilter(django_filters.FilterSet):
    alert_type = django_filters.ChoiceFilter(
        choices=BroadcastAlert.AlertType.choices,
    )

    class Meta:
        model = BroadcastAlert
        fields = ["alert_type", "is_active"]