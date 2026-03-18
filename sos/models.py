import uuid
from django.db import models
from django.conf import settings

from common.models import TimeStampedUUIDModel
from common.validators import latitude_validators, longitude_validators


class SOSAlert(TimeStampedUUIDModel):
    """
    An emergency alert triggered by a student.
    Stores the location where the SOS was activated
    and tracks the lifecycle: active → responding → resolved/cancelled.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESPONDING = "responding", "Responding"
        RESOLVED = "resolved", "Resolved"
        CANCELLED = "cancelled", "Cancelled"
        FALSE_ALARM = "false_alarm", "False Alarm"

    class TriggerMethod(models.TextChoices):
        BUTTON = "button", "SOS Button"
        SHAKE = "shake", "Phone Shake"
        VOICE = "voice", "Voice Command"
        AUTO = "auto", "Automatic"

    # ── Alert identity ──────────────────────────────────
    alert_code = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        help_text="Auto-generated. Format: SOS-YYYYMMDD-XXXXXX",
    )

    # ── Who triggered it ────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sos_alerts",
    )

    # ── When and how ────────────────────────────────────
    triggered_at = models.DateTimeField(auto_now_add=True)
    trigger_method = models.CharField(
        max_length=30,
        choices=TriggerMethod.choices,
        default=TriggerMethod.BUTTON,
    )

    # ── Where ───────────────────────────────────────────
    latitude = models.FloatField(validators=latitude_validators)
    longitude = models.FloatField(validators=longitude_validators)
    accuracy_meters = models.FloatField(null=True, blank=True)
    location_text = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Human-readable location, e.g. 'Near Brunei Hostel'",
    )

    # ── Status ──────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Additional notes from student or security",
    )

    # ── Cancellation ────────────────────────────────────
    cancelled_by_user = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # ── Resolution ──────────────────────────────────────
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_sos_alerts",
    )

    # ── Notifications ───────────────────────────────────
    emergency_contact_notified = models.BooleanField(default=False)

    class Meta:
        db_table = "sos_alerts"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(
                fields=["status", "-triggered_at"],
                name="idx_sos_status_time",
            ),
            models.Index(
                fields=["user", "-triggered_at"],
                name="idx_sos_user_time",
            ),
        ]

    def __str__(self):
        return f"{self.alert_code} — {self.user.full_name} ({self.status})"

    def save(self, *args, **kwargs):
        # Auto-generate alert_code on creation
        if not self.alert_code:
            self.alert_code = self._generate_alert_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_alert_code():
        """Generate a unique alert code: SOS-YYYYMMDD-XXXXXX"""
        from django.utils import timezone

        date_str = timezone.now().strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:6].upper()
        return f"SOS-{date_str}-{random_part}"

    @property
    def is_active(self):
        return self.status in (self.Status.ACTIVE, self.Status.RESPONDING)

    @property
    def response_time_seconds(self):
        """Time from triggered to first response (if any)."""
        if not self.resolved_at:
            return None
        diff = self.resolved_at - self.triggered_at
        return int(diff.total_seconds())


class SOSAlertEvent(models.Model):
    """
    Audit log for every SOS status change or action.
    Gives a full timeline of what happened.
    """

    class EventType(models.TextChoices):
        TRIGGERED = "triggered", "SOS Triggered"
        STATUS_CHANGED = "status_changed", "Status Changed"
        PATROL_ASSIGNED = "patrol_assigned", "Patrol Assigned"
        PATROL_ACCEPTED = "patrol_accepted", "Patrol Accepted"
        PATROL_ARRIVED = "patrol_arrived", "Patrol Arrived"
        NOTE_ADDED = "note_added", "Note Added"
        CONTACT_NOTIFIED = "contact_notified", "Emergency Contact Notified"
        CANCELLED = "cancelled", "Cancelled"
        RESOLVED = "resolved", "Resolved"
        LOCATION_UPDATED = "location_updated", "Location Updated"

    id = models.BigAutoField(primary_key=True)

    sos_alert = models.ForeignKey(
        SOSAlert,
        on_delete=models.CASCADE,
        related_name="events",
    )

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sos_actions",
        help_text="Who performed this action",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra context about the event",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sos_alert_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["sos_alert", "-created_at"],
                name="idx_sos_events_alert_time",
            ),
        ]

    def __str__(self):
        actor = self.actor_user.full_name if self.actor_user else "System"
        return f"{self.sos_alert.alert_code} — {self.event_type} by {actor}"