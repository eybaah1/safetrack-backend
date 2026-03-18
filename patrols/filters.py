import django_filters
from .models import PatrolUnit, SOSAssignment


class PatrolUnitFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=PatrolUnit.Status.choices)

    class Meta:
        model = PatrolUnit
        fields = ["status"]


class SOSAssignmentFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=SOSAssignment.Status.choices)

    sos_alert = django_filters.UUIDFilter(field_name="sos_alert_id")
    patrol_unit = django_filters.UUIDFilter(field_name="patrol_unit_id")

    assigned_after = django_filters.DateTimeFilter(
        field_name="assigned_at",
        lookup_expr="gte",
    )
    assigned_before = django_filters.DateTimeFilter(
        field_name="assigned_at",
        lookup_expr="lte",
    )

    class Meta:
        model = SOSAssignment
        fields = ["status", "sos_alert", "patrol_unit"]