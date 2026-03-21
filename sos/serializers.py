from rest_framework import serializers
from .models import SOSAlert, SOSAlertEvent


class TriggerSOSSerializer(serializers.Serializer):
    """
    POST /api/v1/sos/
    Sent by the student's phone when SOS button is held.
    """

    latitude = serializers.FloatField(
        min_value=-90,
        max_value=90,
        required=False,
        default=6.6745,
    )
    longitude = serializers.FloatField(
        min_value=-180,
        max_value=180,
        required=False,
        default=-1.5716,
    )
    accuracy_meters = serializers.FloatField(
        required=False,
        allow_null=True,
        default=None,
    )
    location_text = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,  # ← THIS FIXES THE ERROR
        default="",
    )
    trigger_method = serializers.ChoiceField(
        choices=SOSAlert.TriggerMethod.choices,
        default="button",
        required=False,
    )
    latitude = serializers.FloatField(
        min_value=-90, max_value=90,
        required=False,
        default=6.6745,
    )
    longitude = serializers.FloatField(
        min_value=-180, max_value=180,
        required=False,
        default=-1.5716,
    )
    accuracy_meters = serializers.FloatField(
        required=False,
        allow_null=True,
        default=None,
    )
    location_text = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
    )
    trigger_method = serializers.ChoiceField(
        choices=SOSAlert.TriggerMethod.choices,
        default="button",
        required=False,
    )
    """
    POST /api/v1/sos/
    Sent by the student's phone when SOS button is held.
    """

    latitude = serializers.FloatField(
        min_value=-90, max_value=90,
        required=False,
        default=6.6742,
    )
    longitude = serializers.FloatField(
        min_value=-180, max_value=180,
        required=False,
        default=-1.5718,
    )
    accuracy_meters = serializers.FloatField(required=False, allow_null=True, default=None)
    location_text = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
    )
    trigger_method = serializers.ChoiceField(
        choices=SOSAlert.TriggerMethod.choices,
        default="button",
        required=False,
    )
    """
    POST /api/v1/sos/
    Sent by the student's phone when SOS button is held.
    """

    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy_meters = serializers.FloatField(required=False, allow_null=True)
    location_text = serializers.CharField(
        max_length=200,
        required=False,
        default="",
    )
    trigger_method = serializers.ChoiceField(
        choices=SOSAlert.TriggerMethod.choices,
        default="button",
        required=False,
    )


class SOSAlertSerializer(serializers.ModelSerializer):
    """
    Full SOS alert for dashboard and detail views.
    Matches what the frontend SOSAlertsPanel and DashboardMap expect.
    """

    student_name = serializers.CharField(source="user.full_name", read_only=True)
    student_id = serializers.SerializerMethodField()
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")
    location = serializers.CharField(source="location_text")
    timestamp = serializers.DateTimeField(source="triggered_at")
    resolved_by_name = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()

    class Meta:
        model = SOSAlert
        fields = [
            "id",
            "alert_code",
            "student_name",
            "student_id",
            "location",
            "lat",
            "lng",
            "accuracy_meters",
            "status",
            "trigger_method",
            "notes",
            "timestamp",
            "cancelled_by_user",
            "cancelled_at",
            "resolved_at",
            "resolved_by_name",
            "emergency_contact_notified",
            "event_count",
            "created_at",
            "updated_at",
        ]

    def get_student_id(self, obj):
        if hasattr(obj.user, "student_profile"):
            return obj.user.student_profile.student_id
        return None

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.full_name
        return None

    def get_event_count(self, obj):
        return obj.events.count()


class SOSAlertCompactSerializer(serializers.ModelSerializer):
    """
    Compact version for the map markers.
    Matches what DashboardMap SOS markers need.
    """

    student_name = serializers.CharField(source="user.full_name")
    student_id = serializers.SerializerMethodField()
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")
    location = serializers.CharField(source="location_text")
    timestamp = serializers.DateTimeField(source="triggered_at")

    class Meta:
        model = SOSAlert
        fields = [
            "id",
            "alert_code",
            "student_name",
            "student_id",
            "location",
            "lat",
            "lng",
            "status",
            "timestamp",
        ]

    def get_student_id(self, obj):
        if hasattr(obj.user, "student_profile"):
            return obj.user.student_profile.student_id
        return None


class SOSAlertEventSerializer(serializers.ModelSerializer):
    """Timeline events for an SOS alert."""

    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = SOSAlertEvent
        fields = [
            "id",
            "event_type",
            "actor_name",
            "details",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if obj.actor_user:
            return obj.actor_user.full_name
        return "System"


class UpdateSOSStatusSerializer(serializers.Serializer):
    """
    PATCH /api/v1/sos/<id>/status/
    Used by security/admin to change SOS status.
    """

    status = serializers.ChoiceField(
        choices=["responding", "resolved", "false_alarm"],
    )
    notes = serializers.CharField(required=False, default="")


class SOSNoteSerializer(serializers.Serializer):
    """
    POST /api/v1/sos/<id>/notes/
    Add a note without changing status.
    """

    note = serializers.CharField(min_length=1)