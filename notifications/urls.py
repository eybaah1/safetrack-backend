from django.urls import path
from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", views.NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("mark-all-read/", views.MarkAllReadView.as_view(), name="mark-all-read"),
    path("clear/", views.ClearAllNotificationsView.as_view(), name="clear-notifications"),
    path("<uuid:id>/read/", views.MarkNotificationReadView.as_view(), name="mark-notification-read"),
    path("<uuid:id>/delete/", views.DeleteNotificationView.as_view(), name="delete-notification"),
    path("broadcasts/", views.BroadcastAlertListView.as_view(), name="broadcast-list"),
    path("broadcasts/create/", views.CreateBroadcastAlertView.as_view(), name="create-broadcast"),
    path("broadcasts/admin/", views.AllBroadcastsAdminView.as_view(), name="broadcast-admin-list"),
    path("broadcasts/<uuid:id>/deactivate/", views.DeactivateBroadcastView.as_view(), name="deactivate-broadcast"),
    path("devices/", views.MyDevicesView.as_view(), name="my-devices"),
    path("devices/register/", views.RegisterDeviceView.as_view(), name="register-device"),
    path("devices/unregister/", views.UnregisterDeviceView.as_view(), name="unregister-device"),
    path("preferences/", views.UserPreferencesView.as_view(), name="user-preferences"),
]