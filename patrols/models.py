from django.db import models
from django.conf import settings

from common.models import TimeStampedUUIDModel
from common.validators import latitude_validators, longitude_validators


class PatrolUnit(TimeStampedUUIDModel):
    """
    A patrol unit that can be dispatched to respond to SOS alerts.
    Appears as yellow markers on the security dashboard map.
    """

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESPONDING = "responding", "Responding"
        ON_BREAK = "on_break", "On Break"
        OFFLINE = "offline", "Offline"

    unit_name = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OFFLINE,
    )

    # ── Current location ────────────────────────────────
    current_lat = models.FloatField(
        null=True,
        blank=True,
        validators=latitude_validators,
    )
    current_lng = models.FloatField(
        null=True,
        blank=True,
        validators=longitude_validators,
    )

    # ── Shift info ──────────────────────────────────────
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)
    area_of_patrol = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="e.g. Main Campus, Brunei Area, Ayeduase",
    )

    class Meta:
        db_table = "patrol_units"
        ordering = ["unit_name"]
        indexes = [
            models.Index(fields=["status"], name="idx_patrol_status"),
        ]

    def __str__(self):
        return f"{self.unit_name} ({self.get_status_display()})"

    @property
    def has_location(self):
        return self.current_lat is not None and self.current_lng is not None

    @property
    def member_count(self):
        return self.members.count()

    @property
    def active_assignment_count(self):
        return self.assignments.filter(
            status__in=["assigned", "accepted", "en_route", "on_scene"],
        ).count()


class PatrolUnitMember(TimeStampedUUIDModel):
    """
    Associates a security user with a patrol unit.
    One security user can only belong to one unit at a time.
    One unit can have multiple members.
    """

    patrol_unit = models.ForeignKey(
        PatrolUnit,
        on_delete=models.CASCADE,
        related_name="members",
    )
    security_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patrol_membership",
        limit_choices_to={"user_role": "security"},
    )
    is_lead = models.BooleanField(
        default=False,
        help_text="Unit lead / team leader",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patrol_unit_members"
        constraints = [
            models.UniqueConstraint(
                fields=["patrol_unit", "security_user"],
                name="uq_patrol_unit_member",
            ),
        ]

    def __str__(self):
        role = "Lead" if self.is_lead else "Member"
        return f"{self.security_user.full_name} → {self.patrol_unit.unit_name} ({role})"


class SOSAssignment(TimeStampedUUIDModel):
    """
    Links an SOS alert to a patrol unit or individual security user.
    Tracks the full response lifecycle.
    """

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        ACCEPTED = "accepted", "Accepted"
        EN_ROUTE = "en_route", "En Route"
        ON_SCENE = "on_scene", "On Scene"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    # ── Links ───────────────────────────────────────────
    sos_alert = models.ForeignKey(
        "sos.SOSAlert",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    patrol_unit = models.ForeignKey(
        PatrolUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    security_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sos_assignments",
        help_text="Individual officer (if no patrol unit)",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_assignments",
    )

    # ── Status ──────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
    )
    notes = models.TextField(blank=True, default="")

    # ── Timestamps ──────────────────────────────────────
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    en_route_at = models.DateTimeField(null=True, blank=True)
    on_scene_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sos_assignments"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(
                fields=["sos_alert", "status"],
                name="idx_assignment_alert_status",
            ),
            models.Index(
                fields=["patrol_unit", "status"],
                name="idx_assignment_patrol_status",
            ),
            models.Index(
                fields=["security_user", "status"],
                name="idx_assignment_security_status",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(patrol_unit__isnull=False)
                    | models.Q(security_user__isnull=False)
                ),
                name="chk_assignment_has_responder",
            ),
        ]

    def __str__(self):
        responder = self.patrol_unit or self.security_user
        return f"{self.sos_alert.alert_code} → {responder} ({self.status})"

    @property
    def responder_name(self):
        if self.patrol_unit:
            return self.patrol_unit.unit_name
        if self.security_user:
            return self.security_user.full_name
        return "Unassigned"

    @property
    def response_time_seconds(self):
        """Time from assignment to arriving on scene."""
        if not self.on_scene_at:
            return None
        diff = self.on_scene_at - self.assigned_at
        return int(diff.total_seconds())