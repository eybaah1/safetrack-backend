from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from common.permissions import IsAdmin
from .models import CampusLocation
from .serializers import (
    CampusLocationListSerializer,
    CampusLocationDetailSerializer,
    CampusLocationMapSerializer,
    CampusLocationAdminSerializer,
)
from .filters import CampusLocationFilter


class CampusLocationListView(generics.ListAPIView):
    """
    GET /api/v1/locations/

    Returns all active campus locations.
    Supports filtering:
      ?location_type=hostel
      ?area=Residential
      ?is_popular=true

    Supports search:
      ?search=library

    Supports ordering:
      ?ordering=name
      ?ordering=-safety_rating
    """

    serializer_class = CampusLocationListSerializer
    permission_classes = [AllowAny]
    filterset_class = CampusLocationFilter
    search_fields = ["name", "location_type", "area", "description"]
    ordering_fields = ["name", "safety_rating", "created_at"]
    ordering = ["name"]
    pagination_class = None  # Return all locations (campus is small)

    def get_queryset(self):
        return CampusLocation.objects.filter(is_active=True)


class CampusLocationSearchView(APIView):
    """
    GET /api/v1/locations/search/?q=hall

    Dedicated search endpoint that matches your frontend SearchModal.
    Searches name, type, and area.
    Returns results grouped with count.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response(
                {"count": 0, "query": "", "results": []},
                status=status.HTTP_200_OK,
            )

        locations = CampusLocation.objects.filter(
            is_active=True,
        ).filter(
            Q(name__icontains=query)
            | Q(location_type__icontains=query)
            | Q(area__icontains=query)
            | Q(description__icontains=query)
        ).order_by("name")

        serializer = CampusLocationListSerializer(locations, many=True)

        return Response(
            {
                "count": locations.count(),
                "query": query,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CampusLocationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/locations/<id>/

    Returns full location details including safety info.
    Used by the Details bottom sheet on the frontend.
    """

    serializer_class = CampusLocationDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        return CampusLocation.objects.filter(is_active=True)


class CampusLocationPopularView(generics.ListAPIView):
    """
    GET /api/v1/locations/popular/

    Returns locations marked as popular.
    Used by SearchModal for the "Popular Locations" section.
    """

    serializer_class = CampusLocationListSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return CampusLocation.objects.filter(
            is_active=True,
            is_popular=True,
        ).order_by("name")


class CampusLocationMapView(generics.ListAPIView):
    """
    GET /api/v1/locations/map/

    Returns minimal data for Leaflet map markers.
    Only id, name, lat, lng — nothing else.
    Optimized for fast map loading.
    """

    serializer_class = CampusLocationMapSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return CampusLocation.objects.filter(
            is_active=True,
        ).only("id", "name", "latitude", "longitude")


class NearbyLocationsView(APIView):
    """
    GET /api/v1/locations/<id>/nearby/

    Returns locations near a given location.
    Simple distance calculation using lat/lng difference.
    Used by the Details component "Nearby Places" section.
    """

    permission_classes = [AllowAny]

    def get(self, request, id):
        try:
            location = CampusLocation.objects.get(id=id, is_active=True)
        except CampusLocation.DoesNotExist:
            return Response(
                {"error": "Location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Simple nearby: find locations within ~500m
        # 0.005 degrees ≈ 500m at KNUST's latitude
        radius = 0.005

        nearby = CampusLocation.objects.filter(
            is_active=True,
            latitude__gte=location.latitude - radius,
            latitude__lte=location.latitude + radius,
            longitude__gte=location.longitude - radius,
            longitude__lte=location.longitude + radius,
        ).exclude(
            id=location.id,
        ).order_by("name")[:5]

        results = []
        for place in nearby:
            # Approximate distance in meters
            lat_diff = abs(place.latitude - location.latitude)
            lng_diff = abs(place.longitude - location.longitude)
            distance_deg = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
            distance_m = int(distance_deg * 111_000)  # rough conversion

            results.append({
                "id": str(place.id),
                "name": place.name,
                "type": place.location_type,
                "distance": f"{distance_m}m",
            })

        return Response(results, status=status.HTTP_200_OK)


# ════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (for security dashboard)
# ════════════════════════════════════════════════════════
class CampusLocationAdminListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/locations/admin/         — list all (including inactive)
    POST /api/v1/locations/admin/         — create new location
    """

    serializer_class = CampusLocationAdminSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_class = CampusLocationFilter
    search_fields = ["name", "location_type", "area"]
    ordering_fields = ["name", "created_at", "safety_rating"]

    def get_queryset(self):
        return CampusLocation.objects.all()


class CampusLocationAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/locations/admin/<id>/  — detail
    PATCH  /api/v1/locations/admin/<id>/  — update
    DELETE /api/v1/locations/admin/<id>/  — delete
    """

    serializer_class = CampusLocationAdminSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"

    def get_queryset(self):
        return CampusLocation.objects.all()