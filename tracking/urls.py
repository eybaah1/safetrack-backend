from django.urls import path
from . import views

urlpatterns = [
    # ── Live location (current user) ────────────────────
    path(
        "live/",
        views.UpdateLiveLocationView.as_view(),
        name="update-live-location",
    ),
    path(
        "live/me/",
        views.MyLiveLocationView.as_view(),
        name="my-live-location",
    ),
    path(
        "sharing/",
        views.ToggleSharingView.as_view(),
        name="toggle-sharing",
    ),

    # ── Nearby users (Walk With Me) ─────────────────────
    path(
        "nearby/",
        views.NearbyUsersView.as_view(),
        name="nearby-users",
    ),

    # ── Security dashboard — live views ─────────────────
    path(
        "live/all/",
        views.AllSharingLocationsView.as_view(),
        name="all-sharing-locations",
    ),
    path(
        "live/<uuid:user_id>/",
        views.UserLiveLocationView.as_view(),
        name="user-live-location",
    ),

    # ── Location history (current user) ─────────────────
    path(
        "history/me/",
        views.MyLocationHistoryView.as_view(),
        name="my-location-history",
    ),
    path(
        "history/",
        views.RecordHistoryView.as_view(),
        name="record-history",
    ),
    path(
        "history/bulk/",
        views.BulkRecordHistoryView.as_view(),
        name="bulk-record-history",
    ),

    # ── Session trails (trip replay) ────────────────────
    path(
        "trail/<str:context>/<uuid:reference_id>/",
        views.SessionTrailView.as_view(),
        name="session-trail",
    ),
    path(
        "participants/<str:context>/<uuid:reference_id>/",
        views.SessionParticipantsLocationView.as_view(),
        name="session-participants",
    ),

    # ── Security — user history ─────────────────────────
    path(
        "history/<uuid:user_id>/",
        views.UserLocationHistoryView.as_view(),
        name="user-location-history",
    ),
]