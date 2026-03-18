from rest_framework import serializers
from .models import CampusLocation


class CampusLocationListSerializer(serializers.ModelSerializer):
    """
    Compact serializer for map markers and search results.
    Returns exactly what Leaflet / SearchModal needs.
    """

    # Frontend expects 'type' not 'location_type'
    type = serializers.CharField(source="location_type")
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = CampusLocation
        fields = [
            "id",
            "name",
            "type",
            "area",
            "lat",
            "lng",
        ]


class CampusLocationDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for the Details bottom sheet.
    Includes safety info and coordinates.
    """

    type = serializers.CharField(source="location_type")
    coordinates = serializers.SerializerMethodField()
    safety_info = serializers.SerializerMethodField()

    class Meta:
        model = CampusLocation
        fields = [
            "id",
            "name",
            "type",
            "area",
            "description",
            "coordinates",
            "safety_info",
            "is_popular",
            "created_at",
            "updated_at",
        ]

    def get_coordinates(self, obj):
        return {
            "lat": obj.latitude,
            "lng": obj.longitude,
        }

    def get_safety_info(self, obj):
        return {
            "rating": obj.safety_rating,
            "lighting": obj.lighting,
            "security_presence": obj.security_presence,
            "recent_activity": obj.recent_activity,
        }


class CampusLocationMapSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for map markers only.
    As light as possible for fast map loading.
    """

    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = CampusLocation
        fields = ["id", "name", "lat", "lng"]


class CampusLocationAdminSerializer(serializers.ModelSerializer):
    """
    Full serializer for admin create/update.
    """

    class Meta:
        model = CampusLocation
        fields = [
            "id",
            "name",
            "location_type",
            "area",
            "description",
            "latitude",
            "longitude",
            "safety_rating",
            "lighting",
            "security_presence",
            "recent_activity",
            "is_active",
            "is_popular",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]