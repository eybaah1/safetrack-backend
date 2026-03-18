from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminOrSecurity
from .models import UserLiveLocation, LocationHistory
from .serializers import (
    UpdateLiveLocationSerializer,
    LiveLocationSerializer,
    LiveLocationMinimalSerializer,
    NearbyUserSerializer,
    LocationHistorySerializer,
    LocationTrailSerializer,
    ParticipantLocationSerializer,
    BulkLocationUploadSerializer,
    ToggleSharingSerializer,
)
from .services import (
    update_live_location,
    record_location_history,
    bulk_record_history,
    toggle_sharing,
    get_nearby_users,
    get_session_trail,
    get_session_participants_locations,
)
from .filters import LocationHistoryFilter


# ════════════════════════════════════════════════════════
# LIVE LOCATION
# ════════════════════════════════════════════════════════

class UpdateLiveLocationView(APIView):
    """
    POST /api/v1/tracking/live/

    Update the current user's live location.
    Called by the device every few seconds during active sessions.
    If context + reference_id are provided, also records to history.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateLiveLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        live_loc, created = update_live_location(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(
            {
                "message": "Location updated.",
                "location": LiveLocationMinimalSerializer(live_loc).data,
            },
            status=status.HTTP_200_OK,
        )


class MyLiveLocationView(APIView):
    """
    GET /api/v1/tracking/live/me/

    Get the current user's last known location.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            loc = UserLiveLocation.objects.select_related("user").get(
                user=request.user,
            )
            return Response(LiveLocationSerializer(loc).data)
        except UserLiveLocation.DoesNotExist:
            return Response(
                {"message": "No location recorded yet."},
                status=status.HTTP_404_NOT_FOUND,
            )


class ToggleSharingView(APIView):
    """
    POST /api/v1/tracking/sharing/

    Turn location sharing on or off.
    Body: { "is_sharing": true }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ToggleSharingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sharing = serializer.validated_data["is_sharing"]
        toggle_sharing(request.user, sharing)

        state = "enabled" if sharing else "disabled"
        return Response(
            {"message": f"Location sharing {state}."},
        )


class NearbyUsersView(APIView):
    """
    GET /api/v1/tracking/nearby/?lat=6.6742&lng=-1.5718&radius=0.5

    Find users near a given location who are actively sharing.
    Used by Walk With Me to find companions.
    Returns users with distance info.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            lat = float(request.query_params.get("lat", 0))
            lng = float(request.query_params.get("lng", 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "lat and lng are required as numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = float(request.query_params.get("radius", 0.5))

        nearby = get_nearby_users(
            latitude=lat,
            longitude=lng,
            radius_km=min(radius, 5.0),  # cap at 5km
            exclude_user=request.user,
        )

        results = []
        for item in nearby:
            loc = item["location"]
            distance_m = item["distance_meters"]

            if distance_m < 1000:
                distance_str = f"{distance_m}m away"
            else:
                distance_str = f"{round(distance_m / 1000, 1)}km away"

            results.append({
                "user_id": str(loc.user.id),
                "name": loc.user.full_name,
                "hostel": loc.user.hostel_name,
                "town": loc.user.town,
                "gender": loc.user.gender,
                "lat": loc.latitude,
                "lng": loc.longitude,
                "distance": distance_str,
                "updated_at": loc.updated_at,
            })

        return Response(
            {
                "count": len(results),
                "center": {"lat": lat, "lng": lng},
                "radius_km": radius,
                "results": results,
            },
        )


# ════════════════════════════════════════════════════════
# SECURITY DASHBOARD — LIVE LOCATIONS
# ════════════════════════════════════════════════════════

class AllSharingLocationsView(generics.ListAPIView):
    """
    GET /api/v1/tracking/live/all/

    All users currently sharing their location.
    Used by the security dashboard to show active students on the map.
    """

    serializer_class = LiveLocationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return UserLiveLocation.objects.filter(
            is_sharing=True,
        ).select_related("user")


class UserLiveLocationView(APIView):
    """
    GET /api/v1/tracking/live/<user_id>/

    Get a specific user's live location.
    Used by security to track a specific student during SOS or walk.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request, user_id):
        try:
            loc = UserLiveLocation.objects.select_related("user").get(
                user_id=user_id,
            )
            return Response(LiveLocationSerializer(loc).data)
        except UserLiveLocation.DoesNotExist:
            return Response(
                {"error": "No location data for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )


# ════════════════════════════════════════════════════════
# LOCATION HISTORY
# ════════════════════════════════════════════════════════

class MyLocationHistoryView(generics.ListAPIView):
    """
    GET /api/v1/tracking/history/me/

    Current user's location history.
    Supports filtering by context and date range.
    """

    serializer_class = LocationHistorySerializer
    permission_classes = [IsAuthenticated]
    filterset_class = LocationHistoryFilter

    def get_queryset(self):
        return LocationHistory.objects.filter(user=self.request.user)


class RecordHistoryView(APIView):
    """
    POST /api/v1/tracking/history/

    Record a single location history entry.
    Used for explicit logging at events like walk start, SOS trigger, etc.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UpdateLiveLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        entry = record_location_history(
            user=request.user,
            latitude=data["latitude"],
            longitude=data["longitude"],
            context=data.get("context", "general"),
            reference_id=data.get("reference_id"),
            accuracy_meters=data.get("accuracy_meters"),
            heading=data.get("heading"),
            speed_mps=data.get("speed_mps"),
        )

        return Response(
            {
                "message": "Location recorded.",
                "entry": LocationHistorySerializer(entry).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BulkRecordHistoryView(APIView):
    """
    POST /api/v1/tracking/history/bulk/

    Upload multiple location entries at once.
    Used for offline sync.
    Body: { "entries": [ { "latitude": ..., "longitude": ..., ... }, ... ] }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BulkLocationUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entries = serializer.validated_data["entries"]
        created = bulk_record_history(user=request.user, entries=entries)

        return Response(
            {
                "message": f"Recorded {len(created)} location entries.",
                "count": len(created),
            },
            status=status.HTTP_201_CREATED,
        )


class SessionTrailView(APIView):
    """
    GET /api/v1/tracking/trail/<context>/<reference_id>/

    Get the full location trail for a session.
    Used for trip history replay — drawing the path on a Leaflet map.

    context: walk, sos, share
    reference_id: UUID of the walk session, SOS alert, or share session
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, context, reference_id):
        valid_contexts = ["walk", "sos", "share"]
        if context not in valid_contexts:
            return Response(
                {"error": f"Invalid context. Use: {valid_contexts}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trail = get_session_trail(context=context, reference_id=reference_id)

        # Students can only see their own trails
        if request.user.user_role == "student":
            trail = trail.filter(user=request.user)

        serializer = LocationTrailSerializer(trail, many=True)

        return Response(
            {
                "context": context,
                "reference_id": str(reference_id),
                "point_count": trail.count(),
                "trail": serializer.data,
            },
        )


class SessionParticipantsLocationView(APIView):
    """
    GET /api/v1/tracking/participants/<context>/<reference_id>/

    Get the latest location of all participants in a session.
    Used during active walks to show all group members on the map.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, context, reference_id):
        valid_contexts = ["walk", "sos", "share"]
        if context not in valid_contexts:
            return Response(
                {"error": f"Invalid context. Use: {valid_contexts}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        locations = get_session_participants_locations(
            context=context,
            reference_id=reference_id,
        )

        serializer = ParticipantLocationSerializer(locations, many=True)

        return Response(
            {
                "context": context,
                "reference_id": str(reference_id),
                "participants": serializer.data,
            },
        )


# ════════════════════════════════════════════════════════
# SECURITY — USER HISTORY
# ════════════════════════════════════════════════════════

class UserLocationHistoryView(generics.ListAPIView):
    """
    GET /api/v1/tracking/history/<user_id>/

    View a specific user's location history.
    Security/admin only — used during SOS investigation.
    """

    serializer_class = LocationHistorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    filterset_class = LocationHistoryFilter

    def get_queryset(self):
        return LocationHistory.objects.filter(
            user_id=self.kwargs["user_id"],
        )