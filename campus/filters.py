import django_filters
from .models import CampusLocation


class CampusLocationFilter(django_filters.FilterSet):
    """
    Supports filtering like:
      ?location_type=hostel
      ?area=Residential
      ?is_popular=true
    """

    location_type = django_filters.ChoiceFilter(
        choices=CampusLocation.LocationType.choices,
    )
    area = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = CampusLocation
        fields = ["location_type", "area", "is_popular"]