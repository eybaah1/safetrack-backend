"""
Aggregation logic for the security dashboard.
Pulls data from sos, patrols, tracking, and walks apps.
No models of its own — pure read-only aggregation.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Avg, F

logger = logging.getLogger(__name__)


def get_dashboard_stats():
    """
    Combined stats for the StatsOverview component.
    Returns everything the frontend DASHBOARD_STATS object needs.
    """
    from sos.models import SOSAlert
    from patrols.models import PatrolUnit, SOSAssignment
    from walks.models import WalkSession
    from tracking.models import UserLiveLocation

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # ── SOS stats ───────────────────────────────────────
    active_alerts = SOSAlert.objects.filter(status="active").count()
    responding_alerts = SOSAlert.objects.filter(status="responding").count()

    resolved_today = SOSAlert.objects.filter(
        status__in=["resolved", "false_alarm"],
        resolved_at__gte=today_start,
    ).count()

    # Average response time (last 7 days)
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

    # ── Patrol stats ────────────────────────────────────
    patrols_on_duty = PatrolUnit.objects.exclude(status="offline").count()
    patrols_available = PatrolUnit.objects.filter(status="available").count()
    patrols_responding = PatrolUnit.objects.filter(status="responding").count()

    active_assignments = SOSAssignment.objects.filter(
        status__in=["assigned", "accepted", "en_route", "on_scene"],
    ).count()

    # ── Walk stats ──────────────────────────────────────
    active_walks = WalkSession.objects.filter(status="active").count()
    pending_groups = WalkSession.objects.filter(
        status="pending", walk_mode="group",
    ).count()

    walks_completed_today = WalkSession.objects.filter(
        status="completed",
        ended_at__gte=today_start,
    ).count()

    arrived_safely_today = WalkSession.objects.filter(
        arrived_safely=True,
        ended_at__gte=today_start,
    ).count()

    # ── Tracking stats ──────────────────────────────────
    students_active = UserLiveLocation.objects.filter(
        is_sharing=True,
        user__user_role="student",
    ).count()

    # ── Totals for the week ─────────────────────────────
    sos_this_week = SOSAlert.objects.filter(
        triggered_at__gte=week_ago,
    ).count()

    walks_this_week = WalkSession.objects.filter(
        created_at__gte=week_ago,
    ).count()

    return {
        "active_alerts": active_alerts,
        "responding_alerts": responding_alerts,
        "total_active_sos": active_alerts + responding_alerts,
        "resolved_today": resolved_today,
        "average_response_time": avg_response_str,

        "patrols_on_duty": patrols_on_duty,
        "patrols_available": patrols_available,
        "patrols_responding": patrols_responding,
        "active_assignments": active_assignments,

        "active_walks": active_walks,
        "pending_groups": pending_groups,
        "walks_completed_today": walks_completed_today,
        "arrived_safely_today": arrived_safely_today,

        "students_active": students_active,

        "sos_this_week": sos_this_week,
        "walks_this_week": walks_this_week,
    }


def get_map_data():
    """
    Combined map data for DashboardMap.
    Returns SOS markers, patrol markers, and active walk markers
    in one response so the frontend only needs one API call.
    """
    from sos.models import SOSAlert
    from patrols.models import PatrolUnit
    from walks.models import WalkSession
    from tracking.models import UserLiveLocation

    # ── SOS markers — use LIVE location if available ────
    sos_alerts = SOSAlert.objects.filter(
        status__in=["active", "responding"],
    ).select_related(
        "user",
        "user__student_profile",
    ).order_by("-triggered_at")

    sos_markers = []
    for alert in sos_alerts:
        student_id = None
        if hasattr(alert.user, "student_profile"):
            student_id = alert.user.student_profile.student_id

        # Try to get LIVE location first (more accurate and current)
        live_lat = alert.latitude
        live_lng = alert.longitude

        try:
            live_loc = UserLiveLocation.objects.get(user=alert.user)
            # Only use live location if it was updated recently (last 5 minutes)
            if live_loc.updated_at > timezone.now() - timedelta(minutes=5):
                live_lat = live_loc.latitude
                live_lng = live_loc.longitude
        except UserLiveLocation.DoesNotExist:
            pass

        sos_markers.append({
            "id": str(alert.id),
            "type": "sos",
            "alert_code": alert.alert_code,
            "student_name": alert.user.full_name,
            "student_id": student_id,
            "location": alert.location_text,
            "lat": live_lat,
            "lng": live_lng,
            "trigger_lat": alert.latitude,
            "trigger_lng": alert.longitude,
            "status": alert.status,
            "timestamp": alert.triggered_at.isoformat(),
        })

    # ── Patrol markers (same as before) ─────────────────
    patrols = PatrolUnit.objects.filter(
        current_lat__isnull=False,
        current_lng__isnull=False,
    ).exclude(status="offline")

    patrol_markers = []
    for patrol in patrols:
        patrol_markers.append({
            "id": str(patrol.id),
            "type": "patrol",
            "name": patrol.unit_name,
            "lat": patrol.current_lat,
            "lng": patrol.current_lng,
            "status": patrol.status,
            "area": patrol.area_of_patrol,
        })

    # ── Active walk markers (same as before) ────────────
    walks = WalkSession.objects.filter(
        status="active",
    ).select_related(
        "created_by",
        "created_by__student_profile",
    )

    walk_markers = []
    for walk in walks:
        current_lat = walk.origin_lat
        current_lng = walk.origin_lng

        try:
            live_loc = walk.created_by.live_location
            current_lat = live_loc.latitude
            current_lng = live_loc.longitude
        except Exception:
            pass

        student_id = None
        if hasattr(walk.created_by, "student_profile"):
            student_id = walk.created_by.student_profile.student_id

        if current_lat and current_lng:
            walk_markers.append({
                "id": str(walk.id),
                "type": "walk",
                "student_name": walk.created_by.full_name,
                "student_id": student_id,
                "from": walk.origin_name,
                "to": walk.destination_name,
                "lat": current_lat,
                "lng": current_lng,
                "walk_mode": walk.walk_mode,
                "started_at": walk.started_at.isoformat() if walk.started_at else None,
            })

    return {
        "sos_alerts": sos_markers,
        "patrol_units": patrol_markers,
        "active_walks": walk_markers,
        "counts": {
            "sos": len(sos_markers),
            "patrols": len(patrol_markers),
            "walks": len(walk_markers),
        },
    }


def get_heatmap_data(days=7):
    """
    Heatmap data based on SOS alert density.
    Returns lat/lng + intensity that the frontend DashboardMap expects.
    """
    from sos.models import SOSAlert

    cutoff = timezone.now() - timedelta(days=days)

    alerts = SOSAlert.objects.filter(
        triggered_at__gte=cutoff,
    ).values("latitude", "longitude")

    if not alerts.exists():
        return _default_heatmap()

    # Group by approximate grid (~100m squares)
    seen = {}
    for loc in alerts:
        key = (round(loc["latitude"], 3), round(loc["longitude"], 3))
        seen[key] = seen.get(key, 0) + 1

    max_count = max(seen.values()) if seen else 1

    result = []
    for (lat, lng), count in seen.items():
        intensity = round(min(count / max_count + 0.2, 1.0), 2)
        result.append({
            "lat": lat,
            "lng": lng,
            "intensity": intensity,
        })

    return result


def _default_heatmap():
    """Fallback heatmap when no real SOS data exists."""
    return [
        {"lat": 6.6731, "lng": -1.5672, "intensity": 0.4},
        {"lat": 6.6738, "lng": -1.5725, "intensity": 0.3},
        {"lat": 6.6782, "lng": -1.5689, "intensity": 0.3},
        {"lat": 6.6805, "lng": -1.5678, "intensity": 0.2},
        {"lat": 6.6698, "lng": -1.5645, "intensity": 0.3},
    ]


def get_activity_feed(limit=20):
    """
    Recent activity across all apps for the dashboard feed.
    Combines SOS events, walk completions, and patrol assignments.
    Returns a chronologically sorted list.
    """
    from sos.models import SOSAlert
    from walks.models import WalkSession
    from patrols.models import SOSAssignment

    now = timezone.now()
    yesterday = now - timedelta(hours=24)

    activities = []

    # Recent SOS alerts
    recent_sos = SOSAlert.objects.filter(
        triggered_at__gte=yesterday,
    ).select_related("user").order_by("-triggered_at")[:limit]

    for alert in recent_sos:
        activities.append({
            "id": str(alert.id),
            "type": "sos",
            "title": f"SOS Alert — {alert.user.full_name}",
            "description": alert.location_text or "Unknown location",
            "status": alert.status,
            "timestamp": alert.triggered_at.isoformat(),
            "severity": "high" if alert.status == "active" else "medium",
        })

    # Recent walk completions
    recent_walks = WalkSession.objects.filter(
        updated_at__gte=yesterday,
        status__in=["active", "completed"],
    ).select_related("created_by").order_by("-updated_at")[:limit]

    for walk in recent_walks:
        if walk.status == "completed":
            title = f"Walk Completed — {walk.created_by.full_name}"
            severity = "low"
        else:
            title = f"Walk Active — {walk.created_by.full_name}"
            severity = "info"

        activities.append({
            "id": str(walk.id),
            "type": "walk",
            "title": title,
            "description": f"{walk.origin_name or 'Start'} → {walk.destination_name}",
            "status": walk.status,
            "timestamp": walk.updated_at.isoformat(),
            "severity": severity,
        })

    # Recent patrol assignments
    recent_assignments = SOSAssignment.objects.filter(
        assigned_at__gte=yesterday,
    ).select_related(
        "sos_alert",
        "patrol_unit",
        "security_user",
    ).order_by("-assigned_at")[:limit]

    for assignment in recent_assignments:
        responder = (
            assignment.patrol_unit.unit_name
            if assignment.patrol_unit
            else assignment.security_user.full_name
            if assignment.security_user
            else "Unknown"
        )

        activities.append({
            "id": str(assignment.id),
            "type": "assignment",
            "title": f"Patrol Assigned — {responder}",
            "description": f"Responding to {assignment.sos_alert.alert_code}",
            "status": assignment.status,
            "timestamp": assignment.assigned_at.isoformat(),
            "severity": "medium",
        })

    # Sort all by timestamp descending
    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    return activities[:limit]


def get_daily_summary():
    """
    End-of-day summary for the dashboard.
    """
    from sos.models import SOSAlert
    from walks.models import WalkSession
    from patrols.models import SOSAssignment
    from accounts.models import User

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    sos_triggered = SOSAlert.objects.filter(
        triggered_at__gte=today_start,
    ).count()

    sos_resolved = SOSAlert.objects.filter(
        status__in=["resolved", "false_alarm"],
        resolved_at__gte=today_start,
    ).count()

    sos_still_active = SOSAlert.objects.filter(
        status__in=["active", "responding"],
    ).count()

    walks_total = WalkSession.objects.filter(
        created_at__gte=today_start,
    ).count()

    walks_completed = WalkSession.objects.filter(
        status="completed",
        ended_at__gte=today_start,
    ).count()

    walks_safely = WalkSession.objects.filter(
        arrived_safely=True,
        ended_at__gte=today_start,
    ).count()

    assignments_made = SOSAssignment.objects.filter(
        assigned_at__gte=today_start,
    ).count()

    assignments_closed = SOSAssignment.objects.filter(
        status="closed",
        closed_at__gte=today_start,
    ).count()

    new_users = User.objects.filter(
        created_at__gte=today_start,
    ).count()

    pending_approvals = User.objects.filter(
        account_status="pending",
    ).count()

    return {
        "date": today_start.date().isoformat(),
        "sos": {
            "triggered": sos_triggered,
            "resolved": sos_resolved,
            "still_active": sos_still_active,
        },
        "walks": {
            "total": walks_total,
            "completed": walks_completed,
            "arrived_safely": walks_safely,
        },
        "assignments": {
            "made": assignments_made,
            "closed": assignments_closed,
        },
        "users": {
            "new_today": new_users,
            "pending_approvals": pending_approvals,
        },
    }


def get_weekly_chart_data():
    """
    Data for a weekly trends chart.
    Returns daily counts for the last 7 days.
    """
    from sos.models import SOSAlert
    from walks.models import WalkSession

    now = timezone.now()
    days = []

    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        sos_count = SOSAlert.objects.filter(
            triggered_at__gte=day_start,
            triggered_at__lt=day_end,
        ).count()

        walk_count = WalkSession.objects.filter(
            created_at__gte=day_start,
            created_at__lt=day_end,
        ).count()

        resolved_count = SOSAlert.objects.filter(
            resolved_at__gte=day_start,
            resolved_at__lt=day_end,
            status__in=["resolved", "false_alarm"],
        ).count()

        days.append({
            "date": day_start.date().isoformat(),
            "day": day_start.strftime("%a"),
            "sos_triggered": sos_count,
            "sos_resolved": resolved_count,
            "walks": walk_count,
        })

    return days