from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdminOrSecurity
from .models import WalkSession, WalkSessionParticipant
from .serializers import (
    CreateWalkSerializer,
    WalkSessionListSerializer,
    WalkSessionDetailSerializer,
    ActiveGroupSerializer,
    WalkHistorySerializer,
    WalkMapSerializer,
)
from .services import (
    create_walk_session,
    join_walk_session,
    leave_walk_session,
    start_walk,
    arrive_safely,
    end_walk,
    cancel_walk,
    get_active_groups,
    get_my_active_walk,
    get_walk_history,
    get_dashboard_walk_stats,
)
from .filters import WalkSessionFilter


# ════════════════════════════════════════════════════════
# CREATE WALK
# ════════════════════════════════════════════════════════

class CreateWalkView(APIView):
    """
    POST /api/v1/walks/

    Create a new walk session.
    Group walks start as 'pending', security walks start as 'active'.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateWalkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        invite_ids = data.pop("invite_user_ids", [])

        try:
            session = create_walk_session(
                creator=request.user,
                **data,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Invite additional users if specified
        if invite_ids:
            from accounts.models import User
            for uid in invite_ids:
                try:
                    user = User.objects.get(id=uid)
                    WalkSessionParticipant.objects.get_or_create(
                        walk_session=session,
                        user=user,
                        defaults={
                            "participant_role": "member",
                            "participant_status": "invited",
                        },
                    )
                except User.DoesNotExist:
                    pass

        return Response(
            {
                "message": "Walk session created.",
                "walk": WalkSessionDetailSerializer(session).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ════════════════════════════════════════════════════════
# ACTIVE GROUPS
# ════════════════════════════════════════════════════════

class ActiveGroupsView(generics.ListAPIView):
    """
    GET /api/v1/walks/active-groups/

    List all joinable group walks.
    Used by WalkWithMeModal "Active Groups" section.
    """

    serializer_class = ActiveGroupSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return get_active_groups(exclude_user=self.request.user)


# ════════════════════════════════════════════════════════
# JOIN / LEAVE
# ════════════════════════════════════════════════════════

class JoinWalkView(APIView):
    """
    POST /api/v1/walks/<id>/join/

    Join an existing group walk.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            session = WalkSession.objects.get(id=id)
        except WalkSession.DoesNotExist:
            return Response(
                {"error": "Walk session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            join_walk_session(session, request.user)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"Joined walk to {session.destination_name}.",
                "walk": WalkSessionDetailSerializer(session).data,
            },
        )


class LeaveWalkView(APIView):
    """
    POST /api/v1/walks/<id>/leave/

    Leave a walk session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            session = WalkSession.objects.get(id=id)
        except WalkSession.DoesNotExist:
            return Response(
                {"error": "Walk session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            leave_walk_session(session, request.user)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "You left the walk session."})


# ════════════════════════════════════════════════════════
# START / ARRIVE / END / CANCEL
# ════════════════════════════════════════════════════════

class StartWalkView(APIView):
    """
    POST /api/v1/walks/<id>/start/

    Start a pending group walk. Turns on sharing for all participants.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            session = WalkSession.objects.get(id=id)
        except WalkSession.DoesNotExist:
            return Response(
                {"error": "Walk session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            session = start_walk(session, started_by=request.user)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Walk started. Location sharing is now active.",
                "walk": WalkSessionDetailSerializer(session).data,
            },
        )


class ArriveSafelyView(APIView):
    """
    POST /api/v1/walks/<id>/arrived/

    Mark that the user arrived safely.
    If creator arrives, the walk is completed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            session = WalkSession.objects.get(id=id)
        except WalkSession.DoesNotExist:
            return Response(
                {"error": "Walk session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            session = arrive_safely(session, user=request.user)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "You arrived safely!",
                "walk": WalkSessionDetailSerializer(session).data,
            },
        )


class EndWalkView(APIView):
    """
    POST /api/v1/walks/<id>/end/

    End an active walk session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            session = WalkSession.objects.get(id=id)
        except WalkSession.DoesNotExist:
            return Response(
                {"error": "Walk session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            session = end_walk(session, ended_by=request.user)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Walk ended.",
                "walk": WalkSessionDetailSerializer(session).data,
            },
        )


class CancelWalkView(APIView):
    """
    POST /api/v1/walks/<id>/cancel/

    Cancel a walk session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            session = WalkSession.objects.get(id=id)
        except WalkSession.DoesNotExist:
            return Response(
                {"error": "Walk session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            session = cancel_walk(session, cancelled_by=request.user)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Walk cancelled.",
                "walk": WalkSessionDetailSerializer(session).data,
            },
        )


# ════════════════════════════════════════════════════════
# MY WALKS
# ════════════════════════════════════════════════════════

class MyActiveWalkView(APIView):
    """
    GET /api/v1/walks/my-active/

    Get the current user's active walk, if any.
    Used to restore ActiveWalkScreen state on reload.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session = get_my_active_walk(request.user)

        if session:
            return Response(
                {
                    "has_active": True,
                    "walk": WalkSessionDetailSerializer(session).data,
                },
            )

        return Response({"has_active": False, "walk": None})


class MyWalkHistoryView(generics.ListAPIView):
    """
    GET /api/v1/walks/my-history/

    Walk history for the Trips page.
    """

    serializer_class = WalkHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_walk_history(self.request.user)


# ════════════════════════════════════════════════════════
# WALK DETAIL
# ════════════════════════════════════════════════════════

class WalkDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/walks/<id>/

    Full walk detail with participants.
    """

    serializer_class = WalkSessionDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return WalkSession.objects.select_related(
            "created_by",
        ).prefetch_related(
            "participants__user",
        )


# ════════════════════════════════════════════════════════
# SECURITY DASHBOARD
# ════════════════════════════════════════════════════════

class AllActiveWalksView(generics.ListAPIView):
    """
    GET /api/v1/walks/active/

    All currently active walks for the security dashboard.
    """

    serializer_class = WalkSessionListSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return WalkSession.objects.filter(
            status="active",
        ).select_related("created_by").order_by("-started_at")


class WalkMapDataView(generics.ListAPIView):
    """
    GET /api/v1/walks/map/

    Active walks with location data for the dashboard map.
    Shows walk creator's current position.
    """

    serializer_class = WalkMapSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return WalkSession.objects.filter(
            status="active",
        ).select_related(
            "created_by",
            "created_by__student_profile",
            "created_by__live_location",
        ).order_by("-started_at")


class WalkStatsView(APIView):
    """
    GET /api/v1/walks/stats/

    Aggregated walk stats for the dashboard.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        stats = get_dashboard_walk_stats()
        return Response(stats)


class AllWalksListView(generics.ListAPIView):
    """
    GET /api/v1/walks/all/

    All walks with filtering (security dashboard).
    """

    serializer_class = WalkSessionListSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    filterset_class = WalkSessionFilter
    search_fields = ["title", "destination_name", "created_by__full_name"]
    ordering_fields = ["created_at", "started_at", "ended_at"]

    def get_queryset(self):
        return WalkSession.objects.select_related("created_by")