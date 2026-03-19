from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsAdminOrSecurity
from .models import SOSAlert, SOSAlertEvent
from .serializers import (
    TriggerSOSSerializer,
    SOSAlertSerializer,
    SOSAlertCompactSerializer,
    SOSAlertEventSerializer,
    UpdateSOSStatusSerializer,
    SOSNoteSerializer,
)
from .services import (
    trigger_sos,
    cancel_sos,
    update_sos_status,
    add_sos_note,
    get_dashboard_sos_stats,
    get_heatmap_data,
)
from .filters import SOSAlertFilter


# ════════════════════════════════════════════════════════
# STUDENT ENDPOINTS
# ════════════════════════════════════════════════════════

class TriggerSOSView(APIView):
    """
    POST /api/v1/sos/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("SOS REQUEST DATA:", request.data)

        serializer = TriggerSOSSerializer(data=request.data)
        if not serializer.is_valid():
            print("SOS VALIDATION ERRORS:", serializer.errors)
            return Response(
                {"error": "Invalid data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            alert, created = trigger_sos(
                user=request.user,
                **serializer.validated_data,
            )
        except Exception as e:
            print("SOS TRIGGER ERROR:", str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = SOSAlertSerializer(alert).data

        if created:
            return Response(
                {"message": "SOS alert sent. Security has been notified.", "alert": response_data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"message": "You already have an active SOS alert.", "alert": response_data},
                status=status.HTTP_200_OK,
            )
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("SOS REQUEST DATA:", request.data)
        serializer = TriggerSOSSerializer(data=request.data)
        if not serializer.is_valid():
            print("SOS VALIDATION ERRORS:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        alert, created = trigger_sos(
            user=request.user,
            **serializer.validated_data,
        )

        response_data = SOSAlertSerializer(alert).data

        if created:
            return Response(
                {"message": "SOS alert sent. Security has been notified.", "alert": response_data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"message": "You already have an active SOS alert.", "alert": response_data},
                status=status.HTTP_200_OK,
            )

class MyActiveSOSView(APIView):
    """
    GET /api/v1/sos/my-active/

    Returns the student's currently active SOS alert, if any.
    Used by EmergencyMode screen to restore state on reload.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        alert = SOSAlert.objects.filter(
            user=request.user,
            status__in=["active", "responding"],
        ).first()

        if alert:
            return Response(
                {
                    "has_active": True,
                    "alert": SOSAlertSerializer(alert).data,
                },
            )

        return Response({"has_active": False, "alert": None})


class CancelSOSView(APIView):
    """
    POST /api/v1/sos/<id>/cancel/

    Student cancels their own SOS.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            alert = SOSAlert.objects.get(id=id)
        except SOSAlert.DoesNotExist:
            return Response(
                {"error": "SOS alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            alert = cancel_sos(alert, cancelled_by_user=request.user)
        except PermissionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "SOS alert cancelled. Security has been notified you are safe.",
                "alert": SOSAlertSerializer(alert).data,
            },
        )


class MySOSHistoryView(generics.ListAPIView):
    """
    GET /api/v1/sos/my-history/

    Student's past SOS alerts (for Trips page).
    """

    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SOSAlert.objects.filter(
            user=self.request.user,
        ).select_related("user", "resolved_by")


# ════════════════════════════════════════════════════════
# SECURITY / ADMIN ENDPOINTS
# ════════════════════════════════════════════════════════

class ActiveSOSListView(generics.ListAPIView):
    """
    GET /api/v1/sos/active/

    All currently active/responding SOS alerts.
    Used by the security dashboard SOSAlertsPanel and DashboardMap.
    """

    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return SOSAlert.objects.filter(
            status__in=["active", "responding"],
        ).select_related(
            "user",
            "user__student_profile",
            "resolved_by",
        ).order_by("-triggered_at")


class AllSOSListView(generics.ListAPIView):
    """
    GET /api/v1/sos/all/

    All SOS alerts with filtering.
    Used by dashboard SOS tab for full history.
    """

    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    filterset_class = SOSAlertFilter
    search_fields = ["alert_code", "user__full_name", "location_text"]
    ordering_fields = ["triggered_at", "status", "resolved_at"]

    def get_queryset(self):
        return SOSAlert.objects.select_related(
            "user",
            "user__student_profile",
            "resolved_by",
        )


class SOSDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/sos/<id>/

    Full SOS alert detail with event count.
    """

    serializer_class = SOSAlertSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    lookup_field = "id"

    def get_queryset(self):
        return SOSAlert.objects.select_related(
            "user",
            "user__student_profile",
            "resolved_by",
        )


class UpdateSOSStatusView(APIView):
    """
    PATCH /api/v1/sos/<id>/status/

    Security/admin changes SOS status.
    e.g. active → responding, responding → resolved
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def patch(self, request, id):
        try:
            alert = SOSAlert.objects.get(id=id)
        except SOSAlert.DoesNotExist:
            return Response(
                {"error": "SOS alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateSOSStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            alert = update_sos_status(
                alert=alert,
                new_status=serializer.validated_data["status"],
                actor_user=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"SOS status updated to '{alert.status}'.",
                "alert": SOSAlertSerializer(alert).data,
            },
        )


class SOSAddNoteView(APIView):
    """
    POST /api/v1/sos/<id>/notes/

    Add a note to an SOS alert without changing status.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def post(self, request, id):
        try:
            alert = SOSAlert.objects.get(id=id)
        except SOSAlert.DoesNotExist:
            return Response(
                {"error": "SOS alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SOSNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        alert = add_sos_note(
            alert=alert,
            actor_user=request.user,
            note_text=serializer.validated_data["note"],
        )

        return Response(
            {"message": "Note added.", "alert": SOSAlertSerializer(alert).data},
        )


class SOSEventTimelineView(generics.ListAPIView):
    """
    GET /api/v1/sos/<id>/events/

    Full event timeline for an SOS alert.
    Shows every status change, note, assignment etc.
    """

    serializer_class = SOSAlertEventSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return SOSAlertEvent.objects.filter(
            sos_alert_id=self.kwargs["id"],
        ).select_related("actor_user").order_by("created_at")


class SOSMapDataView(APIView):
    """
    GET /api/v1/sos/map/

    Returns active SOS alerts in compact format for map markers.
    Used by DashboardMap.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        alerts = SOSAlert.objects.filter(
            status__in=["active", "responding"],
        ).select_related(
            "user",
            "user__student_profile",
        ).order_by("-triggered_at")

        serializer = SOSAlertCompactSerializer(alerts, many=True)
        return Response(serializer.data)


# ════════════════════════════════════════════════════════
# DASHBOARD STATS & HEATMAP
# ════════════════════════════════════════════════════════

class SOSStatsView(APIView):
    """
    GET /api/v1/sos/stats/

    Aggregated SOS stats for the dashboard StatsOverview.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        stats = get_dashboard_sos_stats()
        return Response(stats)


class SOSHeatmapView(APIView):
    """
    GET /api/v1/sos/heatmap/?days=7

    Returns lat/lng + intensity for the heatmap overlay.
    Format matches what the frontend DashboardMap expects.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        days = request.query_params.get("days", 7)
        try:
            days = int(days)
        except (ValueError, TypeError):
            days = 7

        data = get_heatmap_data(days=days)
        return Response(data)
    

class SOSCallInfoView(APIView):
    """
    GET /api/v1/sos/<id>/call-info/

    Returns the student's phone number so security can call them.
    Security/admin only.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request, id):
        try:
            alert = SOSAlert.objects.select_related("user").get(id=id)
        except SOSAlert.DoesNotExist:
            return Response(
                {"error": "SOS alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "student_name": alert.user.full_name,
            "phone": alert.user.phone,
            "email": alert.user.email,
            "alert_code": alert.alert_code,
            "location": alert.location_text,
            "lat": alert.latitude,
            "lng": alert.longitude,
        })