from django.db import models
from django.conf import settings

from common.models import TimeStampedUUIDModel
from common.validators import latitude_validators, longitude_validators


class WalkSession(TimeStampedUUIDModel):
    """
    A Walk With Me session.
    Created when a student wants to walk safely with a group or security escort.
    """

    class Mode(models.TextChoices):
        GROUP = "group", "Group Walk"
        SECURITY = "security", "Security Escort"
        FRIEND = "friend", "Walk With Friend"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending (waiting for members)"
        ACTIVE = "active", "Active (walking)"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    # ── Who created it ──────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_walks",
    )

    # ── Walk details ────────────────────────────────────
    walk_mode = models.CharField(
        max_length=20,
        choices=Mode.choices,
    )
    title = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="e.g. 'Walk to Brunei', 'Library → Ayeduase'",
    )
    max_members = models.PositiveSmallIntegerField(
        default=6,
        help_text="Maximum group size",
    )

    # ── Origin ──────────────────────────────────────────
    origin_name = models.CharField(max_length=150, blank=True, default="")
    origin_lat = models.FloatField(
        null=True, blank=True, validators=latitude_validators,
    )
    origin_lng = models.FloatField(
        null=True, blank=True, validators=longitude_validators,
    )

    # ── Destination ─────────────────────────────────────
    destination_name = models.CharField(max_length=150)
    destination_lat = models.FloatField(
        null=True, blank=True, validators=latitude_validators,
    )
    destination_lng = models.FloatField(
        null=True, blank=True, validators=longitude_validators,
    )

    # ── Status ──────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    monitored_by_security = models.BooleanField(
        default=False,
        help_text="Whether security is monitoring this walk",
    )
    arrived_safely = models.BooleanField(default=False)

    # ── Scheduled departure (for group walks) ───────────
    departure_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Planned departure time for group walks",
    )

    # ── Timestamps ──────────────────────────────────────
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "walk_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "-created_at"],
                name="idx_walk_status_time",
            ),
            models.Index(
                fields=["created_by", "-created_at"],
                name="idx_walk_creator_time",
            ),
        ]

    def __str__(self):
        dest = self.destination_name or "Unknown"
        return f"{self.get_walk_mode_display()} → {dest} ({self.status})"

    @property
    def member_count(self):
        return self.participants.filter(
            participant_status="joined",
        ).count()

    @property
    def is_joinable(self):
        """Can new members still join?"""
        return (
            self.status == self.Status.PENDING
            and self.walk_mode == self.Mode.GROUP
            and self.member_count < self.max_members
        )

    @property
    def duration_minutes(self):
        """Walk duration in minutes."""
        if not self.started_at:
            return 0
        end = self.ended_at or self.updated_at
        diff = end - self.started_at
        return max(int(diff.total_seconds() / 60), 0)


class WalkSessionParticipant(TimeStampedUUIDModel):
    """
    A participant in a walk session.
    Can be the creator, a regular member, or a security monitor.
    """

    class Role(models.TextChoices):
        CREATOR = "creator", "Creator"
        MEMBER = "member", "Member"
        SECURITY_MONITOR = "security_monitor", "Security Monitor"

    class ParticipantStatus(models.TextChoices):
        INVITED = "invited", "Invited"
        JOINED = "joined", "Joined"
        DECLINED = "declined", "Declined"
        LEFT = "left", "Left"

    walk_session = models.ForeignKey(
        WalkSession,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="walk_participations",
    )
    participant_role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    participant_status = models.CharField(
        max_length=20,
        choices=ParticipantStatus.choices,
        default=ParticipantStatus.JOINED,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "walk_session_participants"
        constraints = [
            models.UniqueConstraint(
                fields=["walk_session", "user"],
                name="uq_walk_participant",
            ),
        ]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user.full_name} — {self.get_participant_role_display()} ({self.participant_status})"