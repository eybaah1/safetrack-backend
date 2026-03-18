from rest_framework import serializers


class DashboardStatsSerializer(serializers.Serializer):
    """Matches what the frontend StatsOverview expects."""

    active_alerts = serializers.IntegerField()
    responding_alerts = serializers.IntegerField()
    total_active_sos = serializers.IntegerField()
    resolved_today = serializers.IntegerField()
    average_response_time = serializers.CharField()

    patrols_on_duty = serializers.IntegerField()
    patrols_available = serializers.IntegerField()
    patrols_responding = serializers.IntegerField()
    active_assignments = serializers.IntegerField()

    active_walks = serializers.IntegerField()
    pending_groups = serializers.IntegerField()
    walks_completed_today = serializers.IntegerField()
    arrived_safely_today = serializers.IntegerField()

    students_active = serializers.IntegerField()

    sos_this_week = serializers.IntegerField()
    walks_this_week = serializers.IntegerField()


class MapMarkerSerializer(serializers.Serializer):
    """Single map marker (SOS, patrol, or walk)."""

    id = serializers.CharField()
    type = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    status = serializers.CharField(required=False)


class MapDataSerializer(serializers.Serializer):
    """Combined map data response."""

    sos_alerts = serializers.ListField()
    patrol_units = serializers.ListField()
    active_walks = serializers.ListField()
    counts = serializers.DictField()


class HeatmapPointSerializer(serializers.Serializer):
    """Single heatmap point."""

    lat = serializers.FloatField()
    lng = serializers.FloatField()
    intensity = serializers.FloatField()


class ActivityItemSerializer(serializers.Serializer):
    """Single activity feed item."""

    id = serializers.CharField()
    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    timestamp = serializers.CharField()
    severity = serializers.CharField()


class DailySummarySerializer(serializers.Serializer):
    """Daily summary data."""

    date = serializers.CharField()
    sos = serializers.DictField()
    walks = serializers.DictField()
    assignments = serializers.DictField()
    users = serializers.DictField()


class WeeklyChartDaySerializer(serializers.Serializer):
    """Single day in weekly chart."""

    date = serializers.CharField()
    day = serializers.CharField()
    sos_triggered = serializers.IntegerField()
    sos_resolved = serializers.IntegerField()
    walks = serializers.IntegerField()