from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register(
    r"me/emergency-contacts",
    views.EmergencyContactViewSet,
    basename="emergency-contact",
)
router.register(
    r"me/saved-locations",
    views.SavedLocationViewSet,
    basename="saved-location",
)

urlpatterns = [
    # ── Auth ────────────────────────────────────────────
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # ── Current user ────────────────────────────────────
    path("me/", views.MeView.as_view(), name="me"),
    path("me/photo/", views.MePhotoView.as_view(), name="me-photo"),

    # ── Emergency contacts & saved locations (router) ───
    path("", include(router.urls)),

    # ── Admin approval ──────────────────────────────────
    path(
        "admin/pending-users/",
        views.PendingUsersView.as_view(),
        name="pending-users",
    ),
    path(
        "admin/users/<uuid:user_id>/approve/",
        views.ApproveUserView.as_view(),
        name="approve-user",
    ),
    path(
        "admin/users/<uuid:user_id>/reject/",
        views.RejectUserView.as_view(),
        name="reject-user",
    ),
        # ── Password Reset ──────────────────────────────────
    path("forgot-password/", views.RequestResetCodeView.as_view(), name="forgot-password"),
    path("verify-reset-code/", views.VerifyResetCodeView.as_view(), name="verify-reset-code"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
]