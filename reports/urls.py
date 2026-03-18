from django.urls import path
from . import views

urlpatterns = [
    # ── Student endpoints ───────────────────────────────
    path(
        "",
        views.CreateReportView.as_view(),
        name="create-report",
    ),
    path(
        "my/",
        views.MyReportsView.as_view(),
        name="my-reports",
    ),
    path(
        "my/<uuid:id>/",
        views.MyReportDetailView.as_view(),
        name="my-report-detail",
    ),
    path(
        "my/<uuid:id>/comments/",
        views.StudentAddCommentView.as_view(),
        name="student-add-comment",
    ),

    # ── Admin / security endpoints ──────────────────────
    path(
        "all/",
        views.AllReportsView.as_view(),
        name="all-reports",
    ),
    path(
        "stats/",
        views.ReportStatsView.as_view(),
        name="report-stats",
    ),
    path(
        "map/",
        views.ReportMapDataView.as_view(),
        name="report-map",
    ),
    path(
        "<uuid:id>/",
        views.ReportDetailView.as_view(),
        name="report-detail",
    ),
    path(
        "<uuid:id>/status/",
        views.UpdateReportStatusView.as_view(),
        name="update-report-status",
    ),
    path(
        "<uuid:id>/assign/",
        views.AssignReportView.as_view(),
        name="assign-report",
    ),
    path(
        "<uuid:id>/comments/",
        views.AdminAddCommentView.as_view(),
        name="admin-add-comment",
    ),
]