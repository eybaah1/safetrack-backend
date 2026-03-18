from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsAdminOrSecurity
from .models import PatrolUnit, PatrolUnitMember, SOSAssignment
from .serializers import (
    PatrolUnitListSerializer,
    PatrolUnitMapSerializer,
    PatrolUnitDetailSerializer,
    PatrolUnitCreateUpdateSerializer,
    PatrolUnitMemberSerializer,
    AddMemberSerializer,
    UpdatePatrolLocationSerializer,
    UpdatePatrolStatusSerializer,
    SOSAssignmentSerializer,
    CreateAssignmentSerializer,
    UpdateAssignmentStatusSerializer,
)
from .services import (
    assign_patrol_to_sos,
    update_assignment_status,
    update_patrol_location,
    set_patrol_status,
    get_available_patrols,
    get_patrol_dashboard_stats,
)
from .filters import PatrolUnitFilter, SOSAssignmentFilter


# ════════════════════════════════════════════════════════
# PATROL UNITS
# ════════════════════════════════════════════════════════

class PatrolUnitListView(generics.ListAPIView):
    """
    GET /api/v1/patrols/

    List all patrol units with status and location.
    Used by the security dashboard.
    """

    serializer_class = PatrolUnitListSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    filterset_class = PatrolUnitFilter
    search_fields = ["unit_name", "area_of_patrol"]
    pagination_class = None

    def get_queryset(self):
        return PatrolUnit.objects.prefetch_related("members")


class PatrolUnitMapView(generics.ListAPIView):
    """
    GET /api/v1/patrols/map/

    Minimal patrol data for dashboard map markers.
    Only returns units that have a known location.
    """

    serializer_class = PatrolUnitMapSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return PatrolUnit.objects.filter(
            current_lat__isnull=False,
            current_lng__isnull=False,
        ).exclude(status="offline")


class PatrolUnitDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/patrols/<id>/

    Full patrol unit detail including members.
    """

    serializer_class = PatrolUnitDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    lookup_field = "id"

    def get_queryset(self):
        return PatrolUnit.objects.prefetch_related(
            "members__security_user",
        )


class AvailablePatrolsView(generics.ListAPIView):
    """
    GET /api/v1/patrols/available/

    List patrol units available for assignment.
    Used by the "Assign Patrol" button on the dashboard.
    """

    serializer_class = PatrolUnitListSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return get_available_patrols()


class UpdatePatrolLocationView(APIView):
    """
    PATCH /api/v1/patrols/<id>/location/

    Update a patrol unit's GPS position.
    Called by patrol officers' devices.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def patch(self, request, id):
        try:
            patrol = PatrolUnit.objects.get(id=id)
        except PatrolUnit.DoesNotExist:
            return Response(
                {"error": "Patrol unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdatePatrolLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        patrol = update_patrol_location(
            patrol,
            latitude=serializer.validated_data["latitude"],
            longitude=serializer.validated_data["longitude"],
        )

        return Response(
            {
                "message": f"{patrol.unit_name} location updated.",
                "patrol": PatrolUnitMapSerializer(patrol).data,
            },
        )


class UpdatePatrolStatusView(APIView):
    """
    PATCH /api/v1/patrols/<id>/status/

    Manually change a patrol unit's availability.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def patch(self, request, id):
        try:
            patrol = PatrolUnit.objects.get(id=id)
        except PatrolUnit.DoesNotExist:
            return Response(
                {"error": "Patrol unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdatePatrolStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            patrol = set_patrol_status(
                patrol,
                new_status=serializer.validated_data["status"],
                actor_user=request.user,
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"{patrol.unit_name} is now {patrol.get_status_display()}.",
                "patrol": PatrolUnitListSerializer(patrol).data,
            },
        )


class PatrolStatsView(APIView):
    """
    GET /api/v1/patrols/stats/

    Aggregated patrol stats for the dashboard.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        stats = get_patrol_dashboard_stats()
        return Response(stats)


# ════════════════════════════════════════════════════════
# PATROL UNIT ADMIN (CRUD)
# ════════════════════════════════════════════════════════

class PatrolUnitCreateView(generics.CreateAPIView):
    """
    POST /api/v1/patrols/admin/

    Create a new patrol unit.
    """

    serializer_class = PatrolUnitCreateUpdateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class PatrolUnitAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/patrols/admin/<id>/
    PATCH  /api/v1/patrols/admin/<id>/
    DELETE /api/v1/patrols/admin/<id>/
    """

    serializer_class = PatrolUnitCreateUpdateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"

    def get_queryset(self):
        return PatrolUnit.objects.all()


# ════════════════════════════════════════════════════════
# PATROL UNIT MEMBERS
# ════════════════════════════════════════════════════════

class PatrolMembersView(APIView):
    """
    GET  /api/v1/patrols/<id>/members/     — list members
    POST /api/v1/patrols/<id>/members/     — add member
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, id):
        try:
            patrol = PatrolUnit.objects.get(id=id)
        except PatrolUnit.DoesNotExist:
            return Response(
                {"error": "Patrol unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        members = PatrolUnitMember.objects.filter(
            patrol_unit=patrol,
        ).select_related("security_user")

        serializer = PatrolUnitMemberSerializer(members, many=True)
        return Response(serializer.data)

    def post(self, request, id):
        from accounts.models import User

        try:
            patrol = PatrolUnit.objects.get(id=id)
        except PatrolUnit.DoesNotExist:
            return Response(
                {"error": "Patrol unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data["security_user_id"]

        try:
            security_user = User.objects.get(id=user_id, user_role="security")
        except User.DoesNotExist:
            return Response(
                {"error": "Security user not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if already in a patrol unit
        if hasattr(security_user, "patrol_membership"):
            return Response(
                {"error": f"{security_user.full_name} is already in patrol unit '{security_user.patrol_membership.patrol_unit.unit_name}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member = PatrolUnitMember.objects.create(
            patrol_unit=patrol,
            security_user=security_user,
            is_lead=serializer.validated_data.get("is_lead", False),
        )

        return Response(
            {
                "message": f"{security_user.full_name} added to {patrol.unit_name}.",
                "member": PatrolUnitMemberSerializer(member).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RemovePatrolMemberView(APIView):
    """
    DELETE /api/v1/patrols/<patrol_id>/members/<member_id>/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request, patrol_id, member_id):
        try:
            member = PatrolUnitMember.objects.select_related(
                "security_user", "patrol_unit",
            ).get(
                id=member_id,
                patrol_unit_id=patrol_id,
            )
        except PatrolUnitMember.DoesNotExist:
            return Response(
                {"error": "Member not found in this patrol unit."},
                status=status.HTTP_404_NOT_FOUND,
            )

        name = member.security_user.full_name
        unit = member.patrol_unit.unit_name
        member.delete()

        return Response(
            {"message": f"{name} removed from {unit}."},
        )


# ════════════════════════════════════════════════════════
# SOS ASSIGNMENTS
# ════════════════════════════════════════════════════════

class CreateAssignmentView(APIView):
    """
    POST /api/v1/patrols/assign/

    Assign a patrol unit or officer to an SOS alert.
    This is the "Assign" button on the dashboard SOSAlertsPanel.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def post(self, request):
        from sos.models import SOSAlert
        from accounts.models import User

        serializer = CreateAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the SOS alert
        try:
            sos_alert = SOSAlert.objects.get(
                id=serializer.validated_data["sos_alert_id"],
            )
        except SOSAlert.DoesNotExist:
            return Response(
                {"error": "SOS alert not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not sos_alert.is_active:
            return Response(
                {"error": "This SOS alert is no longer active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get patrol unit or security user
        patrol_unit = None
        security_user = None

        patrol_id = serializer.validated_data.get("patrol_unit_id")
        user_id = serializer.validated_data.get("security_user_id")

        if patrol_id:
            try:
                patrol_unit = PatrolUnit.objects.get(id=patrol_id)
            except PatrolUnit.DoesNotExist:
                return Response(
                    {"error": "Patrol unit not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if user_id:
            try:
                security_user = User.objects.get(id=user_id, user_role="security")
            except User.DoesNotExist:
                return Response(
                    {"error": "Security user not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            assignment = assign_patrol_to_sos(
                sos_alert=sos_alert,
                patrol_unit=patrol_unit,
                security_user=security_user,
                assigned_by=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": f"Assigned {assignment.responder_name} to {sos_alert.alert_code}.",
                "assignment": SOSAssignmentSerializer(assignment).data,
            },
            status=status.HTTP_201_CREATED,
        )


class UpdateAssignmentStatusView(APIView):
    """
    PATCH /api/v1/patrols/assignments/<id>/status/

    Update assignment lifecycle status.
    e.g. accepted → en_route → on_scene → closed
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def patch(self, request, id):
        try:
            assignment = SOSAssignment.objects.select_related(
                "sos_alert", "patrol_unit", "security_user",
            ).get(id=id)
        except SOSAssignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateAssignmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = update_assignment_status(
                assignment=assignment,
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
                "message": f"Assignment updated to '{assignment.status}'.",
                "assignment": SOSAssignmentSerializer(assignment).data,
            },
        )


class SOSAssignmentListView(generics.ListAPIView):
    """
    GET /api/v1/patrols/assignments/

    All assignments with filtering.
    """

    serializer_class = SOSAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    filterset_class = SOSAssignmentFilter
    ordering_fields = ["assigned_at", "status"]

    def get_queryset(self):
        return SOSAssignment.objects.select_related(
            "sos_alert__user",
            "patrol_unit",
            "security_user",
            "assigned_by",
        )


class SOSAssignmentDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/patrols/assignments/<id>/
    """

    serializer_class = SOSAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    lookup_field = "id"

    def get_queryset(self):
        return SOSAssignment.objects.select_related(
            "sos_alert__user",
            "patrol_unit",
            "security_user",
            "assigned_by",
        )


class ActiveAssignmentsView(generics.ListAPIView):
    """
    GET /api/v1/patrols/assignments/active/

    Currently active assignments.
    """

    serializer_class = SOSAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    pagination_class = None

    def get_queryset(self):
        return SOSAssignment.objects.filter(
            status__in=["assigned", "accepted", "en_route", "on_scene"],
        ).select_related(
            "sos_alert__user",
            "patrol_unit",
            "security_user",
            "assigned_by",
        ).order_by("-assigned_at")


class MyAssignmentsView(generics.ListAPIView):
    """
    GET /api/v1/patrols/my-assignments/

    Assignments for the currently logged-in security user.
    Either directly assigned or via their patrol unit.
    """

    serializer_class = SOSAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q

        queryset = SOSAssignment.objects.select_related(
            "sos_alert__user",
            "patrol_unit",
            "security_user",
            "assigned_by",
        )

        # Get assignments where user is directly assigned
        # OR where user's patrol unit is assigned
        q = Q(security_user=user)
        if hasattr(user, "patrol_membership"):
            q |= Q(patrol_unit=user.patrol_membership.patrol_unit)

        return queryset.filter(q).order_by("-assigned_at")
    

class NearbySecurityView(APIView):
    """
    GET /api/v1/patrols/nearby-security/?lat=6.68&lng=-1.57

    Returns all approved security users with their contact info,
    sorted by distance from the given coordinates.
    Used by the "Assign" feature to find closest security personnel.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        from accounts.models import User
        from tracking.models import UserLiveLocation

        try:
            lat = float(request.query_params.get("lat", 0))
            lng = float(request.query_params.get("lng", 0))
        except (ValueError, TypeError):
            lat, lng = 6.6745, -1.5716

        # Get all approved security users
        security_users = User.objects.filter(
            user_role="security",
            account_status="approved",
            is_active=True,
        ).select_related("security_profile")

        results = []
        for sec_user in security_users:
            user_data = {
                "id": str(sec_user.id),
                "name": sec_user.full_name,
                "phone": sec_user.phone,
                "email": sec_user.email,
                "staff_id": sec_user.security_profile.staff_id if hasattr(sec_user, "security_profile") else None,
                "is_on_duty": sec_user.security_profile.is_on_duty if hasattr(sec_user, "security_profile") else False,
                "lat": None,
                "lng": None,
                "distance": None,
                "distance_text": "Unknown",
            }

            # Try to get their live location
            try:
                live_loc = UserLiveLocation.objects.get(user=sec_user)
                user_data["lat"] = live_loc.latitude
                user_data["lng"] = live_loc.longitude

                # Calculate distance
                lat_diff = abs(live_loc.latitude - lat)
                lng_diff = abs(live_loc.longitude - lng)
                distance_deg = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
                distance_m = int(distance_deg * 111_000)
                user_data["distance"] = distance_m

                if distance_m < 1000:
                    user_data["distance_text"] = f"{distance_m}m away"
                else:
                    user_data["distance_text"] = f"{round(distance_m / 1000, 1)}km away"
            except UserLiveLocation.DoesNotExist:
                user_data["distance"] = 999999
                user_data["distance_text"] = "Location unknown"

            # Check if already assigned to a patrol unit
            if hasattr(sec_user, "patrol_membership"):
                user_data["patrol_unit"] = sec_user.patrol_membership.patrol_unit.unit_name
            else:
                user_data["patrol_unit"] = None

            results.append(user_data)

        # Sort by distance (closest first, unknowns last)
        results.sort(key=lambda x: x["distance"] if x["distance"] is not None else 999999)

        return Response({
            "count": len(results),
            "security_personnel": results,
        })