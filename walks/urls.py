from django.urls import path
from . import views

urlpatterns = [
    # ── Create walk ─────────────────────────────────────
    path(
        "",
        views.CreateWalkView.as_view(),
        name="create-walk",
    ),

    # ── Active groups (for joining) ─────────────────────
    path(
        "active-groups/",
        views.ActiveGroupsView.as_view(),
        name="active-groups",
    ),

    # ── My walks ────────────────────────────────────────
    path(
        "my-active/",
        views.MyActiveWalkView.as_view(),
        name="my-active-walk",
    ),
    path(
        "my-history/",
        views.MyWalkHistoryView.as_view(),
        name="my-walk-history",
    ),

    # ── Walk actions ────────────────────────────────────
    path(
        "<uuid:id>/",
        views.WalkDetailView.as_view(),
        name="walk-detail",
    ),
    path(
        "<uuid:id>/join/",
        views.JoinWalkView.as_view(),
        name="join-walk",
    ),
    path(
        "<uuid:id>/leave/",
        views.LeaveWalkView.as_view(),
        name="leave-walk",
    ),
    path(
        "<uuid:id>/start/",
        views.StartWalkView.as_view(),
        name="start-walk",
    ),
    path(
        "<uuid:id>/arrived/",
        views.ArriveSafelyView.as_view(),
        name="arrive-safely",
    ),
    path(
        "<uuid:id>/end/",
        views.EndWalkView.as_view(),
        name="end-walk",
    ),
    path(
        "<uuid:id>/cancel/",
        views.CancelWalkView.as_view(),
        name="cancel-walk",
    ),

    # ── Security dashboard ──────────────────────────────
    path(
        "active/",
        views.AllActiveWalksView.as_view(),
        name="all-active-walks",
    ),
    path(
        "map/",
        views.WalkMapDataView.as_view(),
        name="walk-map-data",
    ),
    path(
        "stats/",
        views.WalkStatsView.as_view(),
        name="walk-stats",
    ),
    path(
        "all/",
        views.AllWalksListView.as_view(),
        name="all-walks",
    ),
]