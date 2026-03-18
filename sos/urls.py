from django.urls import path
from . import views

urlpatterns = [
    # ── Student endpoints ───────────────────────────────
    path(
        "",
        views.TriggerSOSView.as_view(),
        name="trigger-sos",
    ),
    path(
        "my-active/",
        views.MyActiveSOSView.as_view(),
        name="my-active-sos",
    ),
    path(
        "my-history/",
        views.MySOSHistoryView.as_view(),
        name="my-sos-history",
    ),
    path(
        "<uuid:id>/cancel/",
        views.CancelSOSView.as_view(),
        name="cancel-sos",
    ),

    # ── Security / admin endpoints ──────────────────────
    path(
        "active/",
        views.ActiveSOSListView.as_view(),
        name="active-sos-list",
    ),
    path(
        "all/",
        views.AllSOSListView.as_view(),
        name="all-sos-list",
    ),
    path(
        "stats/",
        views.SOSStatsView.as_view(),
        name="sos-stats",
    ),
    path(
        "map/",
        views.SOSMapDataView.as_view(),
        name="sos-map-data",
    ),
    path(
        "heatmap/",
        views.SOSHeatmapView.as_view(),
        name="sos-heatmap",
    ),
    path(
        "<uuid:id>/",
        views.SOSDetailView.as_view(),
        name="sos-detail",
    ),
    path(
        "<uuid:id>/status/",
        views.UpdateSOSStatusView.as_view(),
        name="update-sos-status",
    ),
    path(
        "<uuid:id>/notes/",
        views.SOSAddNoteView.as_view(),
        name="add-sos-note",
    ),
    path(
        "<uuid:id>/events/",
        views.SOSEventTimelineView.as_view(),
        name="sos-event-timeline",
    ),

        path(
        "<uuid:id>/call-info/",
        views.SOSCallInfoView.as_view(),
        name="sos-call-info",
    ),
]