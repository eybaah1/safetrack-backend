from rest_framework import serializers
from .models import WalkSession, WalkSessionParticipant


# ────────────────────────────────────────────────────────
# Participants
# ────────────────────────────────────────────────────────
class WalkParticipantSerializer(serializers.ModelSerializer):
    """Participant info for walk detail views."""

    user_id = serializers.UUIDField(source="user.id")
    name = serializers.CharField(source="user.full_name")
    hostel = serializers.CharField(source="user.hostel_name")
    role = serializers.CharField(source="participant_role")
    status = serializers.CharField(source="participant_status")

    class Meta:
        model = WalkSessionParticipant
        fields = [
            "id",
            "user_id",
            "name",
            "hostel",
            "role",
            "status",
            "joined_at",
            "left_at",
        ]


# ────────────────────────────────────────────────────────
# Walk Sessions
# ────────────────────────────────────────────────────────
class CreateWalkSerializer(serializers.Serializer):
    """
    POST /api/v1/walks/
    Create a new walk session.
    """

    walk_mode = serializers.ChoiceField(choices=WalkSession.Mode.choices)
    destination_name = serializers.CharField(max_length=150)
    destination_lat = serializers.FloatField(
        required=False, allow_null=True, min_value=-90, max_value=90,
    )
    destination_lng = serializers.FloatField(
        required=False, allow_null=True, min_value=-180, max_value=180,
    )
    title = serializers.CharField(max_length=150, required=False, default="")
    max_members = serializers.IntegerField(
        required=False, default=6, min_value=2, max_value=20,
    )
    origin_name = serializers.CharField(max_length=150, required=False, default="")
    origin_lat = serializers.FloatField(
        required=False, allow_null=True, min_value=-90, max_value=90,
    )
    origin_lng = serializers.FloatField(
        required=False, allow_null=True, min_value=-180, max_value=180,
    )
    departure_time = serializers.DateTimeField(required=False, allow_null=True)

    # Optional: invite specific users
    invite_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        max_length=20,
    )


class WalkSessionListSerializer(serializers.ModelSerializer):
    """
    For listing walks — dashboard and active groups.
    Matches what the frontend WalkWithMeModal expects.
    """

    creator_name = serializers.CharField(source="created_by.full_name")
    member_count = serializers.IntegerField(read_only=True)
    is_joinable = serializers.BooleanField(read_only=True)
    duration = serializers.IntegerField(
        source="duration_minutes", read_only=True,
    )
    mode = serializers.CharField(source="walk_mode")

    class Meta:
        model = WalkSession
        fields = [
            "id",
            "title",
            "mode",
            "status",
            "destination_name",
            "origin_name",
            "creator_name",
            "member_count",
            "max_members",
            "is_joinable",
            "monitored_by_security",
            "arrived_safely",
            "departure_time",
            "started_at",
            "ended_at",
            "duration",
            "created_at",
        ]


class WalkSessionDetailSerializer(serializers.ModelSerializer):
    """
    Full walk detail with participants.
    Used by ActiveWalkScreen and walk detail views.
    """

    creator_name = serializers.CharField(source="created_by.full_name")
    creator_id = serializers.UUIDField(source="created_by.id")
    member_count = serializers.IntegerField(read_only=True)
    is_joinable = serializers.BooleanField(read_only=True)
    duration = serializers.IntegerField(
        source="duration_minutes", read_only=True,
    )
    mode = serializers.CharField(source="walk_mode")
    participants = WalkParticipantSerializer(many=True, read_only=True)

    # Destination and origin coordinates for the map
    destination = serializers.SerializerMethodField()
    origin = serializers.SerializerMethodField()

    class Meta:
        model = WalkSession
        fields = [
            "id",
            "title",
            "mode",
            "status",
            "destination_name",
            "destination",
            "origin_name",
            "origin",
            "creator_name",
            "creator_id",
            "member_count",
            "max_members",
            "is_joinable",
            "monitored_by_security",
            "arrived_safely",
            "departure_time",
            "started_at",
            "ended_at",
            "duration",
            "participants",
            "created_at",
            "updated_at",
        ]

    def get_destination(self, obj):
        if obj.destination_lat and obj.destination_lng:
            return {
                "name": obj.destination_name,
                "lat": obj.destination_lat,
                "lng": obj.destination_lng,
            }
        return {"name": obj.destination_name, "lat": None, "lng": None}

    def get_origin(self, obj):
        if obj.origin_lat and obj.origin_lng:
            return {
                "name": obj.origin_name,
                "lat": obj.origin_lat,
                "lng": obj.origin_lng,
            }
        return {"name": obj.origin_name, "lat": None, "lng": None}


class ActiveGroupSerializer(serializers.ModelSerializer):
    """
    Compact serializer for the "Active Groups" list in WalkWithMeModal.
    Matches the frontend ACTIVE_GROUPS mock data format.
    """

    name = serializers.CharField(source="title")
    destination = serializers.CharField(source="destination_name")
    members = serializers.IntegerField(source="member_count", read_only=True)
    leader = serializers.CharField(source="created_by.full_name")
    hostel = serializers.CharField(source="created_by.hostel_name")

    class Meta:
        model = WalkSession
        fields = [
            "id",
            "name",
            "destination",
            "members",
            "max_members",
            "departure_time",
            "leader",
            "hostel",
        ]


class WalkHistorySerializer(serializers.ModelSerializer):
    """
    For the Trips page history list.
    Matches the frontend trip history format.
    """

    type = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    from_location = serializers.CharField(source="origin_name")
    to_location = serializers.CharField(source="destination_name")
    date = serializers.DateTimeField(source="created_at")
    duration = serializers.SerializerMethodField()

    class Meta:
        model = WalkSession
        fields = [
            "id",
            "type",
            "title",
            "from_location",
            "to_location",
            "status",
            "date",
            "duration",
            "arrived_safely",
        ]

    def get_type(self, obj):
        return "walk"

    def get_title(self, obj):
        mode_titles = {
            "security": "Walk With Security",
            "group": "Walk With Group",
            "friend": "Walk With Friend",
        }
        return mode_titles.get(obj.walk_mode, "Walk")

    def get_duration(self, obj):
        mins = obj.duration_minutes
        if mins == 0:
            return "< 1 min"
        return f"{mins} min"


class WalkMapSerializer(serializers.ModelSerializer):
    """
    Minimal data for showing active walks on the dashboard map.
    """

    student_name = serializers.CharField(source="created_by.full_name")
    student_id = serializers.SerializerMethodField()
    current_lat = serializers.SerializerMethodField()
    current_lng = serializers.SerializerMethodField()

    class Meta:
        model = WalkSession
        fields = [
            "id",
            "student_name",
            "student_id",
            "walk_mode",
            "origin_name",
            "destination_name",
            "status",
            "current_lat",
            "current_lng",
            "started_at",
        ]

    def get_student_id(self, obj):
        if hasattr(obj.created_by, "student_profile"):
            return obj.created_by.student_profile.student_id
        return None

    def get_current_lat(self, obj):
        """Get creator's latest live location."""
        if hasattr(obj.created_by, "live_location"):
            return obj.created_by.live_location.latitude
        return obj.origin_lat

    def get_current_lng(self, obj):
        if hasattr(obj.created_by, "live_location"):
            return obj.created_by.live_location.longitude
        return obj.origin_lng