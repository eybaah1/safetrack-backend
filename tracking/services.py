"""
Business logic for location tracking.
"""

import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def update_live_location(user, latitude, longitude, **kwargs):
    """
    Update or create a user's live location.
    Called every time the device sends a GPS ping.
    Also appends to location history if user is in an active session.
    """
    from .models import UserLiveLocation, LocationHistory

    context = kwargs.get("context", "general")
    reference_id = kwargs.get("reference_id")
    should_share = context in ("walk", "sos", "share")

    live_loc, created = UserLiveLocation.objects.update_or_create(
        user=user,
        defaults={
            "latitude": latitude,
            "longitude": longitude,
            "accuracy_meters": kwargs.get("accuracy_meters"),
            "heading": kwargs.get("heading"),
            "speed_mps": kwargs.get("speed_mps"),
            "source": kwargs.get("source", "gps"),
            "is_sharing": should_share or kwargs.get("is_sharing", False),
        },
    )

    # If there's an active context, also record in history
    if context != "general" and reference_id:
        LocationHistory.objects.create(
            user=user,
            context=context,
            reference_id=reference_id,
            latitude=latitude,
            longitude=longitude,
            accuracy_meters=kwargs.get("accuracy_meters"),
            heading=kwargs.get("heading"),
            speed_mps=kwargs.get("speed_mps"),
        )

    return live_loc, created


def record_location_history(user, latitude, longitude, context="general", reference_id=None, **kwargs):
    from .models import LocationHistory

    entry = LocationHistory.objects.create(
        user=user,
        context=context,
        reference_id=reference_id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=kwargs.get("accuracy_meters"),
        heading=kwargs.get("heading"),
        speed_mps=kwargs.get("speed_mps"),
    )
    return entry


def bulk_record_history(user, entries):
    from .models import LocationHistory

    objects = []
    for entry in entries:
        objects.append(
            LocationHistory(
                user=user,
                latitude=entry["latitude"],
                longitude=entry["longitude"],
                context=entry.get("context", "general"),
                reference_id=entry.get("reference_id"),
                accuracy_meters=entry.get("accuracy_meters"),
                heading=entry.get("heading"),
                speed_mps=entry.get("speed_mps"),
            )
        )

    created = LocationHistory.objects.bulk_create(objects)
    logger.info("Bulk recorded %d location entries for %s", len(created), user.email)
    return created


def toggle_sharing(user, is_sharing):
    """
    Turn location sharing on or off for a user.
    If the user has no live location row yet, skip silently.
    """
    from .models import UserLiveLocation

    updated = UserLiveLocation.objects.filter(user=user).update(
        is_sharing=is_sharing,
    )

    if updated == 0:
        # No live location exists yet — that's OK, just skip
        logger.info(
            "toggle_sharing: no live location for %s, skipping",
            user.email,
        )
        return None

    logger.info(
        "Location sharing %s for %s",
        "enabled" if is_sharing else "disabled",
        user.email,
    )


def get_nearby_users(latitude, longitude, radius_km=0.5, exclude_user=None):
    from .models import UserLiveLocation

    radius_deg = radius_km / 111.0

    queryset = UserLiveLocation.objects.filter(
        is_sharing=True,
        latitude__gte=latitude - radius_deg,
        latitude__lte=latitude + radius_deg,
        longitude__gte=longitude - radius_deg,
        longitude__lte=longitude + radius_deg,
    ).select_related("user")

    if exclude_user:
        queryset = queryset.exclude(user=exclude_user)

    cutoff = timezone.now() - timedelta(minutes=30)
    queryset = queryset.filter(updated_at__gte=cutoff)

    results = []
    for loc in queryset:
        lat_diff = abs(loc.latitude - latitude)
        lng_diff = abs(loc.longitude - longitude)
        distance_deg = (lat_diff ** 2 + lng_diff ** 2) ** 0.5
        distance_m = int(distance_deg * 111_000)

        if distance_m <= radius_km * 1000:
            results.append({
                "location": loc,
                "distance_meters": distance_m,
            })

    results.sort(key=lambda x: x["distance_meters"])
    return results


def get_session_trail(context, reference_id):
    from .models import LocationHistory

    return LocationHistory.objects.filter(
        context=context,
        reference_id=reference_id,
    ).order_by("recorded_at")


def get_session_participants_locations(context, reference_id):
    from .models import LocationHistory
    from django.db.models import Max

    latest_per_user = (
        LocationHistory.objects.filter(
            context=context,
            reference_id=reference_id,
        )
        .values("user")
        .annotate(latest_id=Max("id"))
    )

    latest_ids = [entry["latest_id"] for entry in latest_per_user]

    return LocationHistory.objects.filter(
        id__in=latest_ids,
    ).select_related("user")


def cleanup_old_history(days=90):
    from .models import LocationHistory

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = LocationHistory.objects.filter(
        recorded_at__lt=cutoff,
    ).delete()

    logger.info("Cleaned up %d old location history entries", deleted)
    return deleted


def cleanup_stale_live_locations(hours=24):
    from .models import UserLiveLocation

    cutoff = timezone.now() - timedelta(hours=hours)
    updated = UserLiveLocation.objects.filter(
        is_sharing=True,
        updated_at__lt=cutoff,
    ).update(is_sharing=False)

    if updated:
        logger.info("Marked %d stale live locations as not sharing", updated)
    return updated