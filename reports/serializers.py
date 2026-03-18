from rest_framework import serializers
from .models import IssueReport, ReportComment


# ────────────────────────────────────────────────────────
# Comments
# ────────────────────────────────────────────────────────

class ReportCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()

    class Meta:
        model = ReportComment
        fields = [
            "id",
            "author_name",
            "author_role",
            "comment_text",
            "is_internal",
            "created_at",
        ]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.full_name
        return "System"

    def get_author_role(self, obj):
        if obj.author:
            return obj.author.user_role
        return "system"


class AddCommentSerializer(serializers.Serializer):
    comment_text = serializers.CharField(min_length=1, max_length=2000)
    is_internal = serializers.BooleanField(default=False, required=False)


# ────────────────────────────────────────────────────────
# Issue Reports
# ────────────────────────────────────────────────────────

class CreateReportSerializer(serializers.Serializer):
    """
    POST /api/v1/reports/
    Student creates a new issue report.
    """

    title = serializers.CharField(max_length=150)
    description = serializers.CharField()
    category = serializers.ChoiceField(
        choices=IssueReport.Category.choices,
        default="general",
        required=False,
    )
    priority = serializers.ChoiceField(
        choices=IssueReport.Priority.choices,
        default="medium",
        required=False,
    )
    latitude = serializers.FloatField(
        required=False, allow_null=True, min_value=-90, max_value=90,
    )
    longitude = serializers.FloatField(
        required=False, allow_null=True, min_value=-180, max_value=180,
    )
    location_text = serializers.CharField(
        max_length=200, required=False, default="",
    )
    photo = serializers.ImageField(required=False, allow_null=True)


class IssueReportListSerializer(serializers.ModelSerializer):
    """Compact serializer for listing reports."""

    reported_by_name = serializers.CharField(source="reported_by.full_name")
    assigned_to_name = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    has_photo = serializers.BooleanField(read_only=True)
    has_location = serializers.BooleanField(read_only=True)

    class Meta:
        model = IssueReport
        fields = [
            "id",
            "title",
            "category",
            "priority",
            "status",
            "location_text",
            "reported_by_name",
            "assigned_to_name",
            "comment_count",
            "has_photo",
            "has_location",
            "created_at",
            "resolved_at",
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.full_name
        return None

    def get_comment_count(self, obj):
        return obj.comments.count()


class IssueReportDetailSerializer(serializers.ModelSerializer):
    """Full report detail with comments."""

    reported_by_name = serializers.CharField(source="reported_by.full_name")
    reported_by_email = serializers.CharField(source="reported_by.email")
    reported_by_phone = serializers.CharField(source="reported_by.phone")
    assigned_to_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = IssueReport
        fields = [
            "id",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "location",
            "location_text",
            "photo",
            "reported_by_name",
            "reported_by_email",
            "reported_by_phone",
            "assigned_to",
            "assigned_to_name",
            "resolved_by_name",
            "resolved_at",
            "admin_notes",
            "comments",
            "created_at",
            "updated_at",
        ]

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.full_name
        return None

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.full_name
        return None

    def get_comments(self, obj):
        request = self.context.get("request")
        comments = obj.comments.select_related("author")

        # Students only see non-internal comments
        if request and request.user.user_role == "student":
            comments = comments.filter(is_internal=False)

        return ReportCommentSerializer(comments, many=True).data

    def get_location(self, obj):
        if obj.has_location:
            return {
                "lat": obj.latitude,
                "lng": obj.longitude,
            }
        return None


class UpdateReportStatusSerializer(serializers.Serializer):
    """Admin updates report status."""

    status = serializers.ChoiceField(
        choices=["open", "in_progress", "resolved", "dismissed"],
    )
    admin_notes = serializers.CharField(required=False, default="")


class AssignReportSerializer(serializers.Serializer):
    """Assign a report to a security user."""

    assigned_to_id = serializers.UUIDField()