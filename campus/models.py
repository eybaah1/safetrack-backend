from django.db import models
from common.models import TimeStampedUUIDModel
from common.validators import latitude_validators, longitude_validators


class CampusLocation(TimeStampedUUIDModel):
    """
    A named place on the KNUST campus.
    Used for map markers, search, Walk With Me destinations,
    and location details with safety information.
    """

    class LocationType(models.TextChoices):
        HOSTEL = "hostel", "Hostel"
        FACILITY = "facility", "Facility"
        LANDMARK = "landmark", "Landmark"
        GATE = "gate", "Gate"
        BUS_STOP = "bus_stop", "Bus Stop"
        MEDICAL = "medical", "Medical"
        ACADEMIC = "academic", "Academic"
        SECURITY_POST = "security_post", "Security Post"

    class LightingLevel(models.TextChoices):
        WELL_LIT = "Well lit", "Well lit"
        MODERATELY_LIT = "Moderately lit", "Moderately lit"
        POORLY_LIT = "Poorly lit", "Poorly lit"
        UNLIT = "Unlit", "Unlit"

    class SecurityPresence(models.TextChoices):
        PATROL_AVAILABLE = "Patrol available", "Patrol available"
        SECURITY_POST_NEARBY = "Security post nearby", "Security post nearby"
        LIMITED = "Limited", "Limited"
        NONE = "None", "None"

    # ── Core fields ─────────────────────────────────────
    name = models.CharField(max_length=150, unique=True)
    location_type = models.CharField(
        max_length=50,
        choices=LocationType.choices,
    )
    area = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="e.g. Residential, Academic, Commercial",
    )
    description = models.TextField(blank=True, default="")

    # ── Coordinates ─────────────────────────────────────
    latitude = models.FloatField(validators=latitude_validators)
    longitude = models.FloatField(validators=longitude_validators)

    # ── Safety information ──────────────────────────────
    safety_rating = models.FloatField(
        default=3.0,
        help_text="Safety rating out of 5.0",
    )
    lighting = models.CharField(
        max_length=50,
        choices=LightingLevel.choices,
        default=LightingLevel.MODERATELY_LIT,
    )
    security_presence = models.CharField(
        max_length=50,
        choices=SecurityPresence.choices,
        default=SecurityPresence.LIMITED,
    )
    recent_activity = models.CharField(
        max_length=200,
        blank=True,
        default="Normal activity levels",
    )

    # ── Status ──────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(
        default=False,
        help_text="Show in popular/quick-access lists",
    )

    class Meta:
        db_table = "campus_locations"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"], name="idx_campus_loc_active"),
            models.Index(fields=["location_type"], name="idx_campus_loc_type"),
            models.Index(fields=["is_popular"], name="idx_campus_loc_popular"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"