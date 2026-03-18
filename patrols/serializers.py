from rest_framework import serializers
from .models import PatrolUnit, PatrolUnitMember, SOSAssignment


# ────────────────────────────────────────────────────────
# Patrol Unit Members
# ────────────────────────────────────────────────────────
class PatrolUnitMemberSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="security_user.full_name", read_only=True)
    email = serializers.CharField(source="security_user.email", read_only=True)
    phone = serializers.CharField(source="security_user.phone", read_only=True)
    user_id = serializers.UUIDField(source="security_user.id", read_only=True)

    class Meta:
        model = PatrolUnitMember
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "phone",
            "is_lead",
            "joined_at",
        ]


class AddMemberSerializer(serializers.Serializer):
    """Add a security user to a patrol unit."""

    security_user_id = serializers.UUIDField()
    is_lead = serializers.BooleanField(default=False)


# ────────────────────────────────────────────────────────
# Patrol Units
# ────────────────────────────────────────────────────────
class PatrolUnitListSerializer(serializers.ModelSerializer):
    """
    For the dashboard list and map markers.
    Matches what DashboardMap expects for patrol markers.
    """

    name = serializers.CharField(source="unit_name")
    lat = serializers.FloatField(source="current_lat")
    lng = serializers.FloatField(source="current_lng")
    member_count = serializers.IntegerField(read_only=True)
    active_assignments = serializers.IntegerField(
        source="active_assignment_count",
        read_only=True,
    )

    class Meta:
        model = PatrolUnit
        fields = [
            "id",
            "name",
            "status",
            "lat",
            "lng",
            "area_of_patrol",
            "member_count",
            "active_assignments",
        ]


class PatrolUnitMapSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for map markers only.
    Exactly what DashboardMap patrol markers need.
    """

    name = serializers.CharField(source="unit_name")
    lat = serializers.FloatField(source="current_lat")
    lng = serializers.FloatField(source="current_lng")

    class Meta:
        model = PatrolUnit
        fields = ["id", "name", "lat", "lng", "status"]


class PatrolUnitDetailSerializer(serializers.ModelSerializer):
    """Full detail including members."""

    members = PatrolUnitMemberSerializer(many=True, read_only=True)
    active_assignments = serializers.IntegerField(
        source="active_assignment_count",
        read_only=True,
    )

    class Meta:
        model = PatrolUnit
        fields = [
            "id",
            "unit_name",
            "status",
            "current_lat",
            "current_lng",
            "shift_start",
            "shift_end",
            "area_of_patrol",
            "members",
            "active_assignments",
            "created_at",
            "updated_at",
        ]


class PatrolUnitCreateUpdateSerializer(serializers.ModelSerializer):
    """For creating or updating patrol units."""

    class Meta:
        model = PatrolUnit
        fields = [
            "id",
            "unit_name",
            "status",
            "current_lat",
            "current_lng",
            "shift_start",
            "shift_end",
            "area_of_patrol",
        ]
        read_only_fields = ["id"]


class UpdatePatrolLocationSerializer(serializers.Serializer):
    """Update a patrol unit's current position."""

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class UpdatePatrolStatusSerializer(serializers.Serializer):
    """Manually change patrol status."""

    status = serializers.ChoiceField(
        choices=["available", "on_break", "offline"],
    )


# ────────────────────────────────────────────────────────
# SOS Assignments
# ────────────────────────────────────────────────────────
class SOSAssignmentSerializer(serializers.ModelSerializer):
    """Full assignment detail."""

    alert_code = serializers.CharField(
        source="sos_alert.alert_code",
        read_only=True,
    )
    student_name = serializers.CharField(
        source="sos_alert.user.full_name",
        read_only=True,
    )
    responder_name = serializers.CharField(read_only=True)
    assigned_by_name = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()

    class Meta:
        model = SOSAssignment
        fields = [
            "id",
            "sos_alert_id",
            "alert_code",
            "student_name",
            "patrol_unit_id",
            "security_user_id",
            "responder_name",
            "assigned_by_name",
            "status",
            "notes",
            "assigned_at",
            "accepted_at",
            "en_route_at",
            "on_scene_at",
            "closed_at",
            "response_time",
            "created_at",
            "updated_at",
        ]

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return obj.assigned_by.full_name
        return None

    def get_response_time(self, obj):
        seconds = obj.response_time_seconds
        if seconds is None:
            return None
        minutes = round(seconds / 60, 1)
        return f"{minutes} min"


class CreateAssignmentSerializer(serializers.Serializer):
    """
    POST /api/v1/patrols/assign/
    Assign a patrol unit or individual officer to an SOS alert.
    """

    sos_alert_id = serializers.UUIDField()
    patrol_unit_id = serializers.UUIDField(required=False, allow_null=True)
    security_user_id = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, default="")

    def validate(self, data):
        if not data.get("patrol_unit_id") and not data.get("security_user_id"):
            raise serializers.ValidationError(
                "Must provide either patrol_unit_id or security_user_id."
            )
        return data


class UpdateAssignmentStatusSerializer(serializers.Serializer):
    """Update an assignment's status."""

    status = serializers.ChoiceField(
        choices=["accepted", "en_route", "on_scene", "closed", "cancelled"],
    )
    notes = serializers.CharField(required=False, default="")