from django.db import models
from django.conf import settings

from common.validators import latitude_validators, longitude_validators


class UserLiveLocation(models.Model):
    """
    Single row per user — their most recent known position.
    Overwritten every time the device sends a location update.
    This is what appears on maps (student dots, patrol dots, etc.).
    """

    class Source(models.TextChoices):
        GPS = "gps", "GPS"
        NETWORK = "network", "Network"
        FUSED = "fused", "Fused"
        MANUAL = "manual", "Manual"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="live_location",
    )

    latitude = models.FloatField(validators=latitude_validators)
    longitude = models.FloatField(validators=longitude_validators)
    accuracy_meters = models.FloatField(null=True, blank=True)
    heading = models.FloatField(
        null=True,
        blank=True,
        help_text="Direction in degrees (0-360)",
    )
    speed_mps = models.FloatField(
        null=True,
        blank=True,
        help_text="Speed in meters per second",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.GPS,
    )

    # Whether this user is actively sharing their location
    is_sharing = models.BooleanField(
        default=False,
        help_text="True when user has an active walk, SOS, or share session",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_live_locations"
        indexes = [
            models.Index(
                fields=["-updated_at"],
                name="idx_live_loc_updated",
            ),
        ]

    def __str__(self):
        sharing = "📍 sharing" if self.is_sharing else "hidden"
        return f"{self.user.full_name} ({self.latitude}, {self.longitude}) — {sharing}"


class LocationHistory(models.Model):
    """
    Append-only location log.
    Every location ping during a walk, SOS, or share session is recorded.
    Used for trip history replay and analytics.
    """

    class Context(models.TextChoices):
        GENERAL = "general", "General"
        WALK = "walk", "Walk Session"
        SOS = "sos", "SOS Alert"
        SHARE = "share", "Location Share"

    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location_history",
    )

    context = models.CharField(
        max_length=20,
        choices=Context.choices,
        default=Context.GENERAL,
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the walk session, SOS alert, or share session",
    )

    latitude = models.FloatField(validators=latitude_validators)
    longitude = models.FloatField(validators=longitude_validators)
    accuracy_meters = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    speed_mps = models.FloatField(null=True, blank=True)

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "location_history"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(
                fields=["user", "-recorded_at"],
                name="idx_loc_hist_user_time",
            ),
            models.Index(
                fields=["context", "reference_id", "-recorded_at"],
                name="idx_loc_hist_ctx_ref_time",
            ),
        ]

    def __str__(self):
        return f"{self.user.full_name} @ ({self.latitude}, {self.longitude}) [{self.context}]"