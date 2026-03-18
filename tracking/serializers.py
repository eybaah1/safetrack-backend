from rest_framework import serializers
from .models import UserLiveLocation, LocationHistory


# ────────────────────────────────────────────────────────
# Live Location
# ────────────────────────────────────────────────────────
class UpdateLiveLocationSerializer(serializers.Serializer):
    """
    POST /api/v1/tracking/live/
    Sent by the device every few seconds during an active session.
    """

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy_meters = serializers.FloatField(required=False, allow_null=True)
    heading = serializers.FloatField(required=False, allow_null=True)
    speed_mps = serializers.FloatField(required=False, allow_null=True)
    source = serializers.ChoiceField(
        choices=UserLiveLocation.Source.choices,
        default="gps",
        required=False,
    )

    # Optional: attach to an active session
    context = serializers.ChoiceField(
        choices=LocationHistory.Context.choices,
        default="general",
        required=False,
    )
    reference_id = serializers.UUIDField(required=False, allow_null=True)


class LiveLocationSerializer(serializers.ModelSerializer):
    """
    Returns a user's live location with user info.
    Used for map display.
    """

    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField(source="user.full_name")
    user_role = serializers.CharField(source="user.user_role")
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = UserLiveLocation
        fields = [
            "user_id",
            "name",
            "user_role",
            "lat",
            "lng",
            "accuracy_meters",
            "heading",
            "speed_mps",
            "source",
            "is_sharing",
            "updated_at",
        ]


class LiveLocationMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal live location for map markers.
    """

    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField(source="user.full_name")
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = UserLiveLocation
        fields = ["user_id", "name", "lat", "lng", "is_sharing", "updated_at"]


class NearbyUserSerializer(serializers.Serializer):
    """
    A nearby user with distance info.
    Used by Walk With Me to find companions.
    """

    user_id = serializers.UUIDField()
    name = serializers.CharField()
    hostel = serializers.CharField()
    town = serializers.CharField()
    gender = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    distance = serializers.CharField()
    updated_at = serializers.DateTimeField()


# ────────────────────────────────────────────────────────
# Location History
# ────────────────────────────────────────────────────────
class LocationHistorySerializer(serializers.ModelSerializer):
    """
    Single history entry.
    """

    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = LocationHistory
        fields = [
            "id",
            "context",
            "reference_id",
            "lat",
            "lng",
            "accuracy_meters",
            "heading",
            "speed_mps",
            "recorded_at",
        ]


class LocationTrailSerializer(serializers.ModelSerializer):
    """
    For replaying a session trail on the map.
    Minimal data — just coordinates and timestamps.
    """

    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = LocationHistory
        fields = ["lat", "lng", "recorded_at"]


class ParticipantLocationSerializer(serializers.ModelSerializer):
    """
    Latest location of a session participant.
    Used during active walks to show group members.
    """

    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField(source="user.full_name")
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = LocationHistory
        fields = ["user_id", "name", "lat", "lng", "recorded_at"]


class BulkLocationEntrySerializer(serializers.Serializer):
    """
    Single entry in a bulk location upload.
    """

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy_meters = serializers.FloatField(required=False, allow_null=True)
    heading = serializers.FloatField(required=False, allow_null=True)
    speed_mps = serializers.FloatField(required=False, allow_null=True)
    context = serializers.ChoiceField(
        choices=LocationHistory.Context.choices,
        default="general",
        required=False,
    )
    reference_id = serializers.UUIDField(required=False, allow_null=True)


class BulkLocationUploadSerializer(serializers.Serializer):
    """
    POST /api/v1/tracking/history/bulk/
    Upload multiple location entries at once (offline sync).
    """

    entries = BulkLocationEntrySerializer(many=True, min_length=1, max_length=500)


class ToggleSharingSerializer(serializers.Serializer):
    """
    POST /api/v1/tracking/sharing/
    """

    is_sharing = serializers.BooleanField()