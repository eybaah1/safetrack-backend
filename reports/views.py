from rest_framework import generics, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin, IsAdminOrSecurity
from .models import IssueReport, ReportComment
from .serializers import (
    CreateReportSerializer,
    IssueReportListSerializer,
    IssueReportDetailSerializer,
    ReportCommentSerializer,
    AddCommentSerializer,
    UpdateReportStatusSerializer,
    AssignReportSerializer,
)
from .services import (
    create_report,
    update_report_status,
    assign_report,
    add_comment,
    get_report_stats,
)
from .filters import IssueReportFilter


# ════════════════════════════════════════════════════════
# STUDENT ENDPOINTS
# ════════════════════════════════════════════════════════

class CreateReportView(APIView):
    """
    POST /api/v1/reports/

    Student creates a new issue report.
    Supports multipart for photo upload.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        serializer = CreateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = create_report(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(
            {
                "message": "Report submitted. Thank you for helping keep campus safe!",
                "report": IssueReportDetailSerializer(
                    report,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyReportsView(generics.ListAPIView):
    """
    GET /api/v1/reports/my/

    Student's own reports.
    """

    serializer_class = IssueReportListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return IssueReport.objects.filter(
            reported_by=self.request.user,
        ).select_related("reported_by", "assigned_to")


class MyReportDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/reports/my/<id>/

    Student views their own report detail.
    """

    serializer_class = IssueReportDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return IssueReport.objects.filter(
            reported_by=self.request.user,
        ).select_related("reported_by", "assigned_to", "resolved_by")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class StudentAddCommentView(APIView):
    """
    POST /api/v1/reports/my/<id>/comments/

    Student adds a comment to their own report.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            report = IssueReport.objects.get(
                id=id,
                reported_by=request.user,
            )
        except IssueReport.DoesNotExist:
            return Response(
                {"error": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AddCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = add_comment(
            report=report,
            author=request.user,
            comment_text=serializer.validated_data["comment_text"],
            is_internal=False,  # Students can't add internal notes
        )

        return Response(
            {
                "message": "Comment added.",
                "comment": ReportCommentSerializer(comment).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ════════════════════════════════════════════════════════
# ADMIN / SECURITY ENDPOINTS
# ════════════════════════════════════════════════════════

class AllReportsView(generics.ListAPIView):
    """
    GET /api/v1/reports/all/

    All reports with filtering.
    Security/admin dashboard.
    """

    serializer_class = IssueReportListSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    filterset_class = IssueReportFilter
    search_fields = ["title", "description", "location_text", "reported_by__full_name"]
    ordering_fields = ["created_at", "priority", "status"]

    def get_queryset(self):
        return IssueReport.objects.select_related(
            "reported_by",
            "assigned_to",
        )


class ReportDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/reports/<id>/

    Full report detail. Security/admin.
    """

    serializer_class = IssueReportDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminOrSecurity]
    lookup_field = "id"

    def get_queryset(self):
        return IssueReport.objects.select_related(
            "reported_by",
            "assigned_to",
            "resolved_by",
        ).prefetch_related("comments__author")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class UpdateReportStatusView(APIView):
    """
    PATCH /api/v1/reports/<id>/status/

    Admin/security changes report status.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def patch(self, request, id):
        try:
            report = IssueReport.objects.get(id=id)
        except IssueReport.DoesNotExist:
            return Response(
                {"error": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateReportStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report = update_report_status(
            report=report,
            new_status=serializer.validated_data["status"],
            actor_user=request.user,
            admin_notes=serializer.validated_data.get("admin_notes", ""),
        )

        return Response(
            {
                "message": f"Report status updated to '{report.status}'.",
                "report": IssueReportDetailSerializer(
                    report,
                    context={"request": request},
                ).data,
            },
        )


class AssignReportView(APIView):
    """
    POST /api/v1/reports/<id>/assign/

    Assign a report to a security officer.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, id):
        from accounts.models import User

        try:
            report = IssueReport.objects.get(id=id)
        except IssueReport.DoesNotExist:
            return Response(
                {"error": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AssignReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assigned_to = User.objects.get(
                id=serializer.validated_data["assigned_to_id"],
                user_role__in=["security", "admin"],
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Security user not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        report = assign_report(
            report=report,
            assigned_to=assigned_to,
            assigned_by=request.user,
        )

        return Response(
            {
                "message": f"Report assigned to {assigned_to.full_name}.",
                "report": IssueReportDetailSerializer(
                    report,
                    context={"request": request},
                ).data,
            },
        )


class AdminAddCommentView(APIView):
    """
    POST /api/v1/reports/<id>/comments/

    Admin/security adds a comment (can be internal).
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def post(self, request, id):
        try:
            report = IssueReport.objects.get(id=id)
        except IssueReport.DoesNotExist:
            return Response(
                {"error": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AddCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = add_comment(
            report=report,
            author=request.user,
            comment_text=serializer.validated_data["comment_text"],
            is_internal=serializer.validated_data.get("is_internal", False),
        )

        return Response(
            {
                "message": "Comment added.",
                "comment": ReportCommentSerializer(comment).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ReportCommentsView(generics.ListAPIView):
    """
    GET /api/v1/reports/<id>/comments/

    All comments on a report.
    Students only see non-internal comments.
    """

    serializer_class = ReportCommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        report_id = self.kwargs["id"]
        queryset = ReportComment.objects.filter(
            report_id=report_id,
        ).select_related("author")

        if self.request.user.user_role == "student":
            queryset = queryset.filter(is_internal=False)

        return queryset


class ReportStatsView(APIView):
    """
    GET /api/v1/reports/stats/

    Aggregated report stats for the dashboard.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        stats = get_report_stats()
        return Response(stats)


class ReportMapDataView(APIView):
    """
    GET /api/v1/reports/map/

    Open/in-progress reports with location data for map display.
    """

    permission_classes = [IsAuthenticated, IsAdminOrSecurity]

    def get(self, request):
        reports = IssueReport.objects.filter(
            status__in=["open", "in_progress"],
            latitude__isnull=False,
            longitude__isnull=False,
        ).select_related("reported_by").order_by("-created_at")

        data = []
        for report in reports:
            data.append({
                "id": str(report.id),
                "title": report.title,
                "category": report.category,
                "priority": report.priority,
                "status": report.status,
                "lat": report.latitude,
                "lng": report.longitude,
                "location_text": report.location_text,
                "reported_by": report.reported_by.full_name,
                "created_at": report.created_at.isoformat(),
            })

        return Response(data)