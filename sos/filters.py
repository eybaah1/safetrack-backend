import django_filters
from .models import SOSAlert


class SOSAlertFilter(django_filters.FilterSet):
    """
    Supports filtering like:
      ?status=active
      ?status=responding
      ?trigger_method=button
      ?triggered_after=2025-02-01
      ?triggered_before=2025-02-28
    """

    status = django_filters.ChoiceFilter(choices=SOSAlert.Status.choices)
    trigger_method = django_filters.ChoiceFilter(choices=SOSAlert.TriggerMethod.choices)

    triggered_after = django_filters.DateTimeFilter(
        field_name="triggered_at",
        lookup_expr="gte",
    )
    triggered_before = django_filters.DateTimeFilter(
        field_name="triggered_at",
        lookup_expr="lte",
    )

    class Meta:
        model = SOSAlert
        fields = ["status", "trigger_method"]