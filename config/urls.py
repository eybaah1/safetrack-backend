from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django admin

    path("api/v1/reports/", include("reports.urls")),

    path("api/v1/chats/", include("chat.urls")),

    path("api/v1/walks/", include("walks.urls")),

    path("api/v1/dashboard/", include("dashboard.urls")),

    path("admin/", admin.site.urls),

    path("api/v1/tracking/", include("tracking.urls")),    # ← add this

    path("api/v1/locations/", include("campus.urls")),     # ← add this

    path("api/v1/sos/", include("sos.urls")),            # ← add this

    path("api/v1/patrols/", include("patrols.urls")),    # ← add this

    # API v1
    path("api/v1/auth/", include("accounts.urls")),

    path("api/v1/notifications/", include("notifications.urls")),


    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize admin header
admin.site.site_header = "KNUST SafeTrack Admin"
admin.site.site_title = "SafeTrack"
admin.site.index_title = "Security Dashboard"