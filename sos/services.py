"""
Core business logic for SOS alerts.
Views call these functions — keeps views thin.
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def trigger_sos(user, latitude, longitude, **kwargs):
    """
    Create a new SOS alert for a user.
    Logs the 'triggered' event.
    Returns the created SOSAlert.
    """
    from .models import SOSAlert, SOSAlertEvent

    # Prevent duplicate active SOS from same user
    existing = SOSAlert.objects.filter(
        user=user,
        status__in=["active", "responding"],
    ).first()

    if existing:
        return existing, False  # already has an active SOS

    alert = SOSAlert.objects.create(
        user=user,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=kwargs.get("accuracy_meters"),
        location_text=kwargs.get("location_text", ""),
        trigger_method=kwargs.get("trigger_method", "button"),
    )

    # Log the trigger event
    SOSAlertEvent.objects.create(
        sos_alert=alert,
        actor_user=user,
        event_type="triggered",
        details={
            "latitude": latitude,
            "longitude": longitude,
            "location_text": kwargs.get("location_text", ""),
            "trigger_method": kwargs.get("trigger_method", "button"),
        },
    )

    logger.info(
        "SOS triggered: %s by %s at (%s, %s)",
        alert.alert_code,
        user.email,
        latitude,
        longitude,
    )

    # TODO: notify emergency contacts (notifications app)
    # TODO: push to security dashboard via WebSocket (channels)

    return alert, True  # newly created


def cancel_sos(alert, cancelled_by_user):
    """
    Cancel an active SOS alert.
    Only the student who triggered it can cancel.
    """
    from .models import SOSAlertEvent

    if alert.status not in ("active", "responding"):
        raise ValueError("Only active or responding alerts can be cancelled.")

    if alert.user != cancelled_by_user:
        raise PermissionError("You can only cancel your own SOS alert.")

    now = timezone.now()
    alert.status = "cancelled"
    alert.cancelled_by_user = True
    alert.cancelled_at = now
    alert.save(update_fields=[
        "status", "cancelled_by_user", "cancelled_at", "updated_at",
    ])

    SOSAlertEvent.objects.create(
        sos_alert=alert,
        actor_user=cancelled_by_user,
        event_type="cancelled",
        details={"cancelled_at": now.isoformat()},
    )

    logger.info("SOS cancelled: %s by %s", alert.alert_code, cancelled_by_user.email)
    return alert


def update_sos_status(alert, new_status, actor_user, notes=""):
    """
    Update SOS status (used by security/admin).
    Valid transitions:
      active → responding
      active → resolved
      active → false_alarm
      responding → resolved
      responding → false_alarm
    """
    from .models import SOSAlert, SOSAlertEvent

    valid_transitions = {
        "active": ["responding", "resolved", "false_alarm"],
        "responding": ["resolved", "false_alarm"],
    }

    allowed = valid_transitions.get(alert.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot change status from '{alert.status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    old_status = alert.status
    alert.status = new_status

    if new_status in ("resolved", "false_alarm"):
        alert.resolved_at = timezone.now()
        alert.resolved_by = actor_user

    if notes:
        alert.notes = notes

    update_fields = ["status", "notes", "updated_at"]
    if alert.resolved_at:
        update_fields += ["resolved_at", "resolved_by"]

    alert.save(update_fields=update_fields)

    SOSAlertEvent.objects.create(
        sos_alert=alert,
        actor_user=actor_user,
        event_type="status_changed",
        details={
            "old_status": old_status,
            "new_status": new_status,
            "notes": notes,
        },
    )

    logger.info(
        "SOS %s status: %s → %s by %s",
        alert.alert_code,
        old_status,
        new_status,
        actor_user.email,
    )

    return alert


def add_sos_note(alert, actor_user, note_text):
    """Add a note to an SOS alert without changing status."""
    from .models import SOSAlertEvent

    SOSAlertEvent.objects.create(
        sos_alert=alert,
        actor_user=actor_user,
        event_type="note_added",
        details={"note": note_text},
    )

    # Append to alert notes
    if alert.notes:
        alert.notes += f"\n---\n{note_text}"
    else:
        alert.notes = note_text
    alert.save(update_fields=["notes", "updated_at"])

    return alert


def get_dashboard_sos_stats():
    """
    Aggregated stats for the security dashboard StatsOverview.
    """
    from .models import SOSAlert
    from django.db.models import Avg, F
    from datetime import timedelta

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_count = SOSAlert.objects.filter(status="active").count()
    responding_count = SOSAlert.objects.filter(status="responding").count()

    resolved_today = SOSAlert.objects.filter(
        status__in=["resolved", "false_alarm"],
        resolved_at__gte=today_start,
    ).count()

    # Average response time for resolved alerts in last 7 days
    week_ago = now - timedelta(days=7)
    avg_response = SOSAlert.objects.filter(
        status="resolved",
        resolved_at__gte=week_ago,
        resolved_at__isnull=False,
    ).annotate(
        response_seconds=F("resolved_at") - F("triggered_at"),
    ).aggregate(
        avg_seconds=Avg("response_seconds"),
    )

    avg_time = avg_response.get("avg_seconds")
    if avg_time:
        avg_minutes = round(avg_time.total_seconds() / 60, 1)
        avg_response_str = f"{avg_minutes} min"
    else:
        avg_response_str = "N/A"

    # Total alerts this week
    total_this_week = SOSAlert.objects.filter(
        triggered_at__gte=week_ago,
    ).count()

    return {
        "active_alerts": active_count,
        "responding_alerts": responding_count,
        "total_active": active_count + responding_count,
        "resolved_today": resolved_today,
        "average_response_time": avg_response_str,
        "total_this_week": total_this_week,
    }


def get_heatmap_data(days=7):
    """
    Return lat/lng + intensity data for the heatmap.
    Based on SOS alert density in the last N days.
    Matches the frontend HEATMAP_DATA format.
    """
    from .models import SOSAlert
    from datetime import timedelta
    from django.db.models import Count

    cutoff = timezone.now() - timedelta(days=days)

    # Get all SOS locations in the period
    alerts = SOSAlert.objects.filter(
        triggered_at__gte=cutoff,
    ).values("latitude", "longitude")

    if not alerts.exists():
        # Return campus hotspot defaults if no real data yet
        return _default_heatmap_data()

    # Group nearby alerts and calculate intensity
    # Simple approach: return each alert location with intensity
    # based on how many alerts are nearby
    locations = list(alerts)
    max_count = len(locations) or 1

    # For now, return each unique-ish location with normalized intensity
    seen = {}
    for loc in locations:
        # Round to ~100m grid
        key = (round(loc["latitude"], 3), round(loc["longitude"], 3))
        seen[key] = seen.get(key, 0) + 1

    result = []
    for (lat, lng), count in seen.items():
        intensity = round(min(count / max_count + 0.3, 1.0), 2)
        result.append({
            "lat": lat,
            "lng": lng,
            "intensity": intensity,
        })

    return result


def _default_heatmap_data():
    """
    Fallback heatmap data when no real SOS alerts exist.
    Uses known campus hotspots.
    """
    return [
        {"lat": 6.6731, "lng": -1.5672, "intensity": 0.4},  # JQB
        {"lat": 6.6738, "lng": -1.5725, "intensity": 0.3},  # Library
        {"lat": 6.6782, "lng": -1.5689, "intensity": 0.3},  # Hall 7
        {"lat": 6.6805, "lng": -1.5678, "intensity": 0.2},  # Brunei
        {"lat": 6.6698, "lng": -1.5645, "intensity": 0.3},  # Ayeduase
    ]