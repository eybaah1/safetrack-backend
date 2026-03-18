import django_filters
from .models import WalkSession


class WalkSessionFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=WalkSession.Status.choices)
    walk_mode = django_filters.ChoiceFilter(choices=WalkSession.Mode.choices)

    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    destination = django_filters.CharFilter(
        field_name="destination_name",
        lookup_expr="icontains",
    )

    class Meta:
        model = WalkSession
        fields = ["status", "walk_mode"]