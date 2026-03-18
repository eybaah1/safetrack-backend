from django.urls import path
from . import views

urlpatterns = [
    # ── Patrol units ────────────────────────────────────
    path(
        "",
        views.PatrolUnitListView.as_view(),
        name="patrol-list",
    ),
    path(
        "map/",
        views.PatrolUnitMapView.as_view(),
        name="patrol-map",
    ),
    path(
        "available/",
        views.AvailablePatrolsView.as_view(),
        name="patrol-available",
    ),
    path(
        "stats/",
        views.PatrolStatsView.as_view(),
        name="patrol-stats",
    ),
    path(
        "<uuid:id>/",
        views.PatrolUnitDetailView.as_view(),
        name="patrol-detail",
    ),
    path(
        "<uuid:id>/location/",
        views.UpdatePatrolLocationView.as_view(),
        name="patrol-update-location",
    ),
    path(
        "<uuid:id>/status/",
        views.UpdatePatrolStatusView.as_view(),
        name="patrol-update-status",
    ),

    # ── Patrol members ──────────────────────────────────
    path(
        "<uuid:id>/members/",
        views.PatrolMembersView.as_view(),
        name="patrol-members",
    ),
    path(
        "<uuid:patrol_id>/members/<uuid:member_id>/",
        views.RemovePatrolMemberView.as_view(),
        name="patrol-remove-member",
    ),

    # ── Admin CRUD ──────────────────────────────────────
    path(
        "admin/",
        views.PatrolUnitCreateView.as_view(),
        name="patrol-create",
    ),
    path(
        "admin/<uuid:id>/",
        views.PatrolUnitAdminDetailView.as_view(),
        name="patrol-admin-detail",
    ),

    # ── SOS Assignments ─────────────────────────────────
    path(
        "assign/",
        views.CreateAssignmentView.as_view(),
        name="create-assignment",
    ),
    path(
        "assignments/",
        views.SOSAssignmentListView.as_view(),
        name="assignment-list",
    ),
    path(
        "assignments/active/",
        views.ActiveAssignmentsView.as_view(),
        name="assignment-active",
    ),
    path(
        "assignments/<uuid:id>/",
        views.SOSAssignmentDetailView.as_view(),
        name="assignment-detail",
    ),
    path(
        "assignments/<uuid:id>/status/",
        views.UpdateAssignmentStatusView.as_view(),
        name="assignment-update-status",
    ),
    path(
        "my-assignments/",
        views.MyAssignmentsView.as_view(),
        name="my-assignments",
    ),

    path(
        "nearby-security/",
        views.NearbySecurityView.as_view(),
        name="nearby-security",
    ),
]