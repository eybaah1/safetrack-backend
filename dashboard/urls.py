from django.urls import path
from . import views

urlpatterns = [
    # ── Individual endpoints ────────────────────────────
    path(
        "stats/",
        views.DashboardStatsView.as_view(),
        name="dashboard-stats",
    ),
    path(
        "map/",
        views.DashboardMapView.as_view(),
        name="dashboard-map",
    ),
    path(
        "heatmap/",
        views.DashboardHeatmapView.as_view(),
        name="dashboard-heatmap",
    ),
    path(
        "activity/",
        views.DashboardActivityFeedView.as_view(),
        name="dashboard-activity",
    ),
    path(
        "summary/",
        views.DashboardSummaryView.as_view(),
        name="dashboard-summary",
    ),
    path(
        "weekly/",
        views.DashboardWeeklyChartView.as_view(),
        name="dashboard-weekly",
    ),

    # ── All-in-one endpoint ─────────────────────────────
    path(
        "overview/",
        views.DashboardOverviewView.as_view(),
        name="dashboard-overview",
    ),
]