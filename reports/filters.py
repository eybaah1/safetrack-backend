import django_filters
from .models import IssueReport


class IssueReportFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=IssueReport.Status.choices)
    category = django_filters.ChoiceFilter(choices=IssueReport.Category.choices)
    priority = django_filters.ChoiceFilter(choices=IssueReport.Priority.choices)

    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    location = django_filters.CharFilter(
        field_name="location_text",
        lookup_expr="icontains",
    )

    class Meta:
        model = IssueReport
        fields = ["status", "category", "priority"]