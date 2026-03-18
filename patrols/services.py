"""
Business logic for patrol units and SOS assignments.
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def assign_patrol_to_sos(sos_alert, patrol_unit=None, security_user=None, assigned_by=None, notes=""):
    """
    Assign a patrol unit or individual officer to an SOS alert.
    Also updates the patrol unit status to 'responding'
    and the SOS alert status to 'responding'.
    """
    from .models import SOSAssignment, PatrolUnit
    from sos.models import SOSAlertEvent

    if not patrol_unit and not security_user:
        raise ValueError("Must provide either patrol_unit or security_user.")

    # Check if this patrol is already assigned to this SOS
    existing = SOSAssignment.objects.filter(
        sos_alert=sos_alert,
        status__in=["assigned", "accepted", "en_route", "on_scene"],
    )
    if patrol_unit:
        existing = existing.filter(patrol_unit=patrol_unit)
    if security_user:
        existing = existing.filter(security_user=security_user)

    if existing.exists():
        raise ValueError("This responder is already assigned to this SOS alert.")

    # Create assignment
    assignment = SOSAssignment.objects.create(
        sos_alert=sos_alert,
        patrol_unit=patrol_unit,
        security_user=security_user,
        assigned_by=assigned_by,
        notes=notes,
    )

    # Update patrol unit status
    if patrol_unit and patrol_unit.status == PatrolUnit.Status.AVAILABLE:
        patrol_unit.status = PatrolUnit.Status.RESPONDING
        patrol_unit.save(update_fields=["status", "updated_at"])

    # Update SOS status to responding (if currently active)
    if sos_alert.status == "active":
        sos_alert.status = "responding"
        sos_alert.save(update_fields=["status", "updated_at"])

    # Log event on the SOS alert
    responder_name = patrol_unit.unit_name if patrol_unit else security_user.full_name
    SOSAlertEvent.objects.create(
        sos_alert=sos_alert,
        actor_user=assigned_by,
        event_type="patrol_assigned",
        details={
            "assignment_id": str(assignment.id),
            "responder": responder_name,
            "notes": notes,
        },
    )

    logger.info(
        "Patrol assigned: %s → %s (by %s)",
        responder_name,
        sos_alert.alert_code,
        assigned_by.email if assigned_by else "system",
    )

    return assignment


def update_assignment_status(assignment, new_status, actor_user=None, notes=""):
    """
    Update an assignment's status through its lifecycle.
    Valid transitions:
      assigned  → accepted, cancelled
      accepted  → en_route, cancelled
      en_route  → on_scene, cancelled
      on_scene  → closed, cancelled
    """
    from .models import SOSAssignment, PatrolUnit
    from sos.models import SOSAlertEvent

    valid_transitions = {
        "assigned": ["accepted", "cancelled"],
        "accepted": ["en_route", "cancelled"],
        "en_route": ["on_scene", "cancelled"],
        "on_scene": ["closed", "cancelled"],
    }

    allowed = valid_transitions.get(assignment.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Cannot change assignment from '{assignment.status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    now = timezone.now()
    old_status = assignment.status
    assignment.status = new_status

    # Set appropriate timestamp
    timestamp_map = {
        "accepted": "accepted_at",
        "en_route": "en_route_at",
        "on_scene": "on_scene_at",
        "closed": "closed_at",
        "cancelled": "closed_at",
    }
    ts_field = timestamp_map.get(new_status)
    if ts_field:
        setattr(assignment, ts_field, now)

    if notes:
        assignment.notes = notes

    update_fields = ["status", "notes", "updated_at"]
    if ts_field:
        update_fields.append(ts_field)
    assignment.save(update_fields=update_fields)

    # If closed or cancelled, free up the patrol unit
    if new_status in ("closed", "cancelled") and assignment.patrol_unit:
        patrol = assignment.patrol_unit
        # Only set available if no other active assignments
        other_active = patrol.assignments.filter(
            status__in=["assigned", "accepted", "en_route", "on_scene"],
        ).exclude(id=assignment.id).exists()

        if not other_active:
            patrol.status = PatrolUnit.Status.AVAILABLE
            patrol.save(update_fields=["status", "updated_at"])

    # Map event types
    event_type_map = {
        "accepted": "patrol_accepted",
        "on_scene": "patrol_arrived",
        "closed": "resolved",
        "cancelled": "cancelled",
    }
    event_type = event_type_map.get(new_status, "status_changed")

    SOSAlertEvent.objects.create(
        sos_alert=assignment.sos_alert,
        actor_user=actor_user,
        event_type=event_type,
        details={
            "assignment_id": str(assignment.id),
            "old_status": old_status,
            "new_status": new_status,
            "responder": assignment.responder_name,
            "notes": notes,
        },
    )

    logger.info(
        "Assignment %s: %s → %s (SOS: %s)",
        assignment.id,
        old_status,
        new_status,
        assignment.sos_alert.alert_code,
    )

    return assignment


def update_patrol_location(patrol_unit, latitude, longitude):
    """
    Update a patrol unit's current position on the map.
    Called periodically by patrol officers' devices.
    """
    patrol_unit.current_lat = latitude
    patrol_unit.current_lng = longitude
    patrol_unit.save(update_fields=["current_lat", "current_lng", "updated_at"])
    return patrol_unit


def set_patrol_status(patrol_unit, new_status, actor_user=None):
    """
    Manually change a patrol unit's availability status.
    Used when going on/off duty, taking breaks, etc.
    """
    from .models import PatrolUnit

    # Don't allow setting to 'responding' manually
    # That only happens via assignment
    if new_status == PatrolUnit.Status.RESPONDING:
        raise ValueError("Status 'responding' is set automatically via SOS assignment.")

    patrol_unit.status = new_status
    patrol_unit.save(update_fields=["status", "updated_at"])

    logger.info(
        "Patrol %s status → %s (by %s)",
        patrol_unit.unit_name,
        new_status,
        actor_user.email if actor_user else "system",
    )

    return patrol_unit


def get_available_patrols():
    """
    Return all patrol units that can be assigned to a new SOS.
    Used by the assignment UI on the dashboard.
    """
    from .models import PatrolUnit

    return PatrolUnit.objects.filter(
        status=PatrolUnit.Status.AVAILABLE,
    ).prefetch_related("members__security_user")


def get_patrol_dashboard_stats():
    """
    Aggregated patrol stats for the dashboard.
    """
    from .models import PatrolUnit, SOSAssignment

    total = PatrolUnit.objects.count()
    available = PatrolUnit.objects.filter(status="available").count()
    responding = PatrolUnit.objects.filter(status="responding").count()
    offline = PatrolUnit.objects.filter(status="offline").count()
    on_break = PatrolUnit.objects.filter(status="on_break").count()

    active_assignments = SOSAssignment.objects.filter(
        status__in=["assigned", "accepted", "en_route", "on_scene"],
    ).count()

    return {
        "total_units": total,
        "available": available,
        "responding": responding,
        "on_break": on_break,
        "offline": offline,
        "active_assignments": active_assignments,
    }