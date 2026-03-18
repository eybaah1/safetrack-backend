from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminOrSecurity
from .services import (
    get_dashboard_stats,
    get_map_data,
    get_heatmap_data,
    get_activity_feed,
    get_daily_summary,
    get_weekly_chart_data,
)


class DashboardStatsView(APIView):
    """
    GET /api/v1/dashboard/stats/

    Combined stats for the StatsOverview component.
    Single endpoint replaces calling sos/stats + patrols/stats + walks/stats separately.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        stats = get_dashboard_stats()
        return Response(stats)


class DashboardMapView(APIView):
    """
    GET /api/v1/dashboard/map/

    Combined map data — SOS markers, patrol markers, active walks.
    Single endpoint so the DashboardMap only needs one API call.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        data = get_map_data()
        return Response(data)


class DashboardHeatmapView(APIView):
    """
    GET /api/v1/dashboard/heatmap/?days=7

    Heatmap data based on SOS alert density.
    Returns lat/lng + intensity for Leaflet circles.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        days = request.query_params.get("days", 7)
        try:
            days = int(days)
            days = min(max(days, 1), 90)  # clamp between 1 and 90
        except (ValueError, TypeError):
            days = 7

        data = get_heatmap_data(days=days)
        return Response(data)


class DashboardActivityFeedView(APIView):
    """
    GET /api/v1/dashboard/activity/?limit=20

    Recent activity across all apps.
    Combines SOS events, walk completions, patrol assignments.
    Chronologically sorted.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        limit = request.query_params.get("limit", 20)
        try:
            limit = int(limit)
            limit = min(max(limit, 1), 100)
        except (ValueError, TypeError):
            limit = 20

        activities = get_activity_feed(limit=limit)

        return Response({
            "count": len(activities),
            "activities": activities,
        })


class DashboardSummaryView(APIView):
    """
    GET /api/v1/dashboard/summary/

    Today's summary — SOS, walks, assignments, users.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        summary = get_daily_summary()
        return Response(summary)


class DashboardWeeklyChartView(APIView):
    """
    GET /api/v1/dashboard/weekly/

    Daily counts for the last 7 days.
    For rendering trend charts on the dashboard.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        data = get_weekly_chart_data()
        return Response({
            "days": data,
        })


class DashboardOverviewView(APIView):
    """
    GET /api/v1/dashboard/overview/

    Everything the dashboard needs in ONE call.
    Combines stats + map + activity feed.
    Useful for initial dashboard load.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        stats = get_dashboard_stats()
        map_data = get_map_data()
        activity = get_activity_feed(limit=10)
        summary = get_daily_summary()

        return Response({
            "stats": stats,
            "map": map_data,
            "recent_activity": activity,
            "today_summary": summary,
        })