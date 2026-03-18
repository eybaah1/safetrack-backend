from django.urls import path
from . import views

urlpatterns = [
    # ── Public (student app) ────────────────────────────
    path(
        "",
        views.CampusLocationListView.as_view(),
        name="location-list",
    ),
    path(
        "search/",
        views.CampusLocationSearchView.as_view(),
        name="location-search",
    ),
    path(
        "popular/",
        views.CampusLocationPopularView.as_view(),
        name="location-popular",
    ),
    path(
        "map/",
        views.CampusLocationMapView.as_view(),
        name="location-map",
    ),
    path(
        "<uuid:id>/",
        views.CampusLocationDetailView.as_view(),
        name="location-detail",
    ),
    path(
        "<uuid:id>/nearby/",
        views.NearbyLocationsView.as_view(),
        name="location-nearby",
    ),

    # ── Admin (security dashboard) ──────────────────────
    path(
        "admin/",
        views.CampusLocationAdminListCreateView.as_view(),
        name="location-admin-list",
    ),
    path(
        "admin/<uuid:id>/",
        views.CampusLocationAdminDetailView.as_view(),
        name="location-admin-detail",
    ),
]