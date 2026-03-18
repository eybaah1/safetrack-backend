from django.db import models
from django.conf import settings

from common.models import TimeStampedUUIDModel
from common.validators import latitude_validators, longitude_validators


class IssueReport(TimeStampedUUIDModel):
    """
    A safety or infrastructure issue reported by a student.
    Examples: broken streetlight, dark path, suspicious activity,
    damaged walkway, missing signage.
    """

    class Category(models.TextChoices):
        LIGHTING = "lighting", "Broken/Missing Lighting"
        INFRASTRUCTURE = "infrastructure", "Infrastructure Damage"
        SUSPICIOUS = "suspicious", "Suspicious Activity"
        UNSAFE_AREA = "unsafe_area", "Unsafe Area"
        HARASSMENT = "harassment", "Harassment"
        THEFT = "theft", "Theft"
        VANDALISM = "vandalism", "Vandalism"
        SIGNAGE = "signage", "Missing/Damaged Signage"
        OTHER = "other", "Other"
        GENERAL = "general", "General"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    # ── Who reported it ─────────────────────────────────
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issue_reports",
    )

    # ── Report details ──────────────────────────────────
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    # ── Location ────────────────────────────────────────
    latitude = models.FloatField(
        null=True,
        blank=True,
        validators=latitude_validators,
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        validators=longitude_validators,
    )
    location_text = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="e.g. 'Near Tech Junction', 'Behind Engineering Block'",
    )

    # ── Photo evidence ──────────────────────────────────
    photo = models.ImageField(
        upload_to="report_photos/",
        null=True,
        blank=True,
    )

    # ── Status tracking ─────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    admin_notes = models.TextField(
        blank=True,
        default="",
        help_text="Internal notes from security/admin",
    )

    # ── Resolution ──────────────────────────────────────
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_reports",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ── Assignment ──────────────────────────────────────
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_reports",
        help_text="Security officer or admin assigned to handle this",
    )

    class Meta:
        db_table = "issue_reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="idx_report_status_time",
            ),
            models.Index(
                fields=["reported_by", "-created_at"],
                name="idx_report_user_time",
            ),
            models.Index(
                fields=["category"],
                name="idx_report_category",
            ),
            models.Index(
                fields=["priority"],
                name="idx_report_priority",
            ),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title} — {self.reported_by.full_name}"

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def has_photo(self):
        return bool(self.photo)


class ReportComment(TimeStampedUUIDModel):
    """
    Comments on a report.
    Used for back-and-forth between student and admin/security.
    """

    report = models.ForeignKey(
        IssueReport,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_comments",
    )
    comment_text = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal notes only visible to admin/security",
    )

    class Meta:
        db_table = "report_comments"
        ordering = ["created_at"]

    def __str__(self):
        author_name = self.author.full_name if self.author else "System"
        return f"{author_name}: {self.comment_text[:50]}"