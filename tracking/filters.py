import django_filters
from .models import LocationHistory


class LocationHistoryFilter(django_filters.FilterSet):
    """
    Supports filtering like:
      ?context=walk
      ?context=sos
      ?reference_id=<uuid>
      ?recorded_after=2025-02-01T00:00:00Z
      ?recorded_before=2025-02-28T00:00:00Z
    """

    context = django_filters.ChoiceFilter(choices=LocationHistory.Context.choices)
    reference_id = django_filters.UUIDFilter()

    recorded_after = django_filters.DateTimeFilter(
        field_name="recorded_at",
        lookup_expr="gte",
    )
    recorded_before = django_filters.DateTimeFilter(
        field_name="recorded_at",
        lookup_expr="lte",
    )

    class Meta:
        model = LocationHistory
        fields = ["context", "reference_id"]