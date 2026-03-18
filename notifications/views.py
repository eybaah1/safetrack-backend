from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsAdminOrSecurity
from .models import Notification, BroadcastAlert, UserDevice, UserPreference
from .serializers import (
    NotificationSerializer,
    BroadcastAlertSerializer,
    CreateBroadcastAlertSerializer,
    RegisterDeviceSerializer,
    UserDeviceSerializer,
    UserPreferenceSerializer,
)
from .services import (
    mark_notification_read,
    mark_all_read,
    get_unread_count,
    create_broadcast_alert,
    get_active_broadcasts,
    register_device,
    unregister_device,
)
from .filters import NotificationFilter, BroadcastAlertFilter


# ════════════════════════════════════════════════════════
# PERSONAL NOTIFICATIONS
# ════════════════════════════════════════════════════════

class NotificationListView(generics.ListAPIView):
    """
    GET /api/v1/notifications/

    List current user's notifications.
    Supports filtering: ?is_read=false&notification_type=sos
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = NotificationFilter

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationUnreadCountView(APIView):
    """
    GET /api/v1/notifications/unread-count/

    Total unread notification count.
    Used for badge numbers in the app.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = get_unread_count(request.user)
        return Response({"unread_count": count})


class MarkNotificationReadView(APIView):
    """
    POST /api/v1/notifications/<id>/read/

    Mark a single notification as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            notification = Notification.objects.get(
                id=id,
                user=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mark_notification_read(notification)
        return Response({"message": "Notification marked as read."})


class MarkAllReadView(APIView):
    """
    POST /api/v1/notifications/mark-all-read/

    Mark all of the current user's notifications as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = mark_all_read(request.user)
        return Response(
            {"message": f"Marked {count} notification(s) as read."},
        )


class DeleteNotificationView(APIView):
    """
    DELETE /api/v1/notifications/<id>/

    Delete a single notification.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        deleted, _ = Notification.objects.filter(
            id=id,
            user=request.user,
        ).delete()

        if deleted:
            return Response({"message": "Notification deleted."})
        return Response(
            {"error": "Notification not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


class ClearAllNotificationsView(APIView):
    """
    DELETE /api/v1/notifications/clear/

    Delete all read notifications for the current user.
    Keeps unread notifications.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted, _ = Notification.objects.filter(
            user=request.user,
            is_read=True,
        ).delete()

        return Response(
            {"message": f"Cleared {deleted} read notification(s)."},
        )


# ════════════════════════════════════════════════════════
# BROADCAST ALERTS
# ════════════════════════════════════════════════════════

class BroadcastAlertListView(generics.ListAPIView):
    """
    GET /api/v1/notifications/broadcasts/

    Active broadcast alerts for the current user's role.
    Used by the Alerts page.
    """

    serializer_class = BroadcastAlertSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = BroadcastAlertFilter
    pagination_class = None

    def get_queryset(self):
        user_role = self.request.user.user_role
        return get_active_broadcasts(user_role=user_role)


class CreateBroadcastAlertView(APIView):
    """
    POST /api/v1/notifications/broadcasts/

    Admin/security creates a campus-wide alert.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def post(self, request):
        serializer = CreateBroadcastAlertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        alert = create_broadcast_alert(
            published_by=request.user,
            **serializer.validated_data,
        )

        return Response(
            {
                "message": "Broadcast alert published.",
                "alert": BroadcastAlertSerializer(alert).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DeactivateBroadcastView(APIView):
    """
    POST /api/v1/notifications/broadcasts/<id>/deactivate/

    Deactivate a broadcast alert.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def post(self, request, id):
        try:
            alert = BroadcastAlert.objects.get(id=id)
        except BroadcastAlert.DoesNotExist:
            return Response(
                {"error": "Broadcast alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        alert.is_active = False
        alert.save(update_fields=["is_active", "updated_at"])

        return Response({"message": "Broadcast alert deactivated."})


class AllBroadcastsAdminView(generics.ListAPIView):
    """
    GET /api/v1/notifications/broadcasts/admin/

    All broadcasts including inactive. Admin only.
    """

    serializer_class = BroadcastAlertSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_class = BroadcastAlertFilter

    def get_queryset(self):
        return BroadcastAlert.objects.all()


# ════════════════════════════════════════════════════════
# DEVICE REGISTRATION
# ════════════════════════════════════════════════════════

class RegisterDeviceView(APIView):
    """
    POST /api/v1/notifications/devices/

    Register a device for push notifications.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RegisterDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device, created = register_device(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(
            {
                "message": "Device registered." if created else "Device updated.",
                "device": UserDeviceSerializer(device).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnregisterDeviceView(APIView):
    """
    POST /api/v1/notifications/devices/unregister/

    Unregister a device. Body: { "device_token": "..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_token = request.data.get("device_token")
        if not device_token:
            return Response(
                {"error": "device_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        success = unregister_device(device_token)

        if success:
            return Response({"message": "Device unregistered."})
        return Response(
            {"error": "Device not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


class MyDevicesView(generics.ListAPIView):
    """
    GET /api/v1/notifications/devices/

    List current user's registered devices.
    """

    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return UserDevice.objects.filter(
            user=self.request.user,
            is_active=True,
        )


# ════════════════════════════════════════════════════════
# USER PREFERENCES (SETTINGS)
# ════════════════════════════════════════════════════════

class UserPreferencesView(APIView):
    """
    GET  /api/v1/notifications/preferences/    — get my preferences
    PATCH /api/v1/notifications/preferences/   — update preferences
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = UserPreference.objects.get_or_create(
            user=request.user,
        )
        serializer = UserPreferenceSerializer(prefs)
        return Response(serializer.data)

    def patch(self, request):
        prefs, _ = UserPreference.objects.get_or_create(
            user=request.user,
        )
        serializer = UserPreferenceSerializer(
            prefs,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Preferences updated.",
                "preferences": serializer.data,
            },
        )