"""
Business logic for Walk With Me sessions.
Integrates with tracking app for location sharing.
"""

import logging
from django.utils import timezone
from django.db.models import Q, Count

logger = logging.getLogger(__name__)


def _toggle_participant_sharing(walk_session, is_sharing):
    """
    Turn location sharing on/off for all joined participants.
    """
    try:
        from tracking.services import toggle_sharing

        participants = walk_session.participants.filter(
            participant_status="joined",
        ).select_related("user")

        for participant in participants:
            toggle_sharing(participant.user, is_sharing)

    except ImportError:
        logger.warning("Tracking app not available — skipping sharing toggle")


def _record_participant_locations(walk_session, context="walk"):
    """
    Record current location of all participants in location history.
    """
    try:
        from tracking.models import UserLiveLocation
        from tracking.services import record_location_history

        participants = walk_session.participants.filter(
            participant_status="joined",
        ).values_list("user_id", flat=True)

        live_locations = UserLiveLocation.objects.filter(
            user_id__in=participants,
        )

        for loc in live_locations:
            record_location_history(
                user=loc.user,
                latitude=loc.latitude,
                longitude=loc.longitude,
                context=context,
                reference_id=walk_session.id,
                accuracy_meters=loc.accuracy_meters,
            )

    except ImportError:
        logger.warning("Tracking app not available — skipping location recording")


# ────────────────────────────────────────────────────────
# CREATE WALK
# ────────────────────────────────────────────────────────
def create_walk_session(creator, walk_mode, destination_name, **kwargs):
    """
    Create a new walk session and add the creator as a participant.

    For security mode → also sets monitored_by_security = True.
    For group mode → session stays 'pending' until started.
    """
    from .models import WalkSession, WalkSessionParticipant

    # Prevent creating if user already has an active walk
    existing = WalkSession.objects.filter(
        participants__user=creator,
        participants__participant_status="joined",
        status__in=["pending", "active"],
    ).first()

    if existing:
        raise ValueError(
            "You already have an active walk session. "
            "End it before starting a new one."
        )

    is_security_mode = walk_mode == "security"

    session = WalkSession.objects.create(
        created_by=creator,
        walk_mode=walk_mode,
        destination_name=destination_name,
        title=kwargs.get("title", ""),
        max_members=kwargs.get("max_members", 6),
        origin_name=kwargs.get("origin_name", ""),
        origin_lat=kwargs.get("origin_lat"),
        origin_lng=kwargs.get("origin_lng"),
        destination_lat=kwargs.get("destination_lat"),
        destination_lng=kwargs.get("destination_lng"),
        departure_time=kwargs.get("departure_time"),
        monitored_by_security=is_security_mode,
        # Security walks start immediately, group walks wait for members
        status="active" if is_security_mode else "pending",
        started_at=timezone.now() if is_security_mode else None,
    )

    # Add creator as participant
    WalkSessionParticipant.objects.create(
        walk_session=session,
        user=creator,
        participant_role="creator",
        participant_status="joined",
    )

    # If security mode, turn on sharing immediately
    if is_security_mode:
        _toggle_participant_sharing(session, True)

    logger.info(
        "Walk session created: %s by %s → %s (%s)",
        session.id,
        creator.email,
        destination_name,
        walk_mode,
    )

    # Create walk group chat
    try:
        from chat.services import create_walk_chat
        create_walk_chat(session)
    except Exception as exc:
        logger.warning("Failed to create walk chat: %s", exc)

    return session


# ────────────────────────────────────────────────────────
# JOIN / LEAVE
# ────────────────────────────────────────────────────────
def join_walk_session(session, user):
    """
    Join an existing walk session.
    Only works for group walks that are pending and not full.
    """
    from .models import WalkSession, WalkSessionParticipant

    if not session.is_joinable:
        if session.status != "pending":
            raise ValueError("This walk has already started or ended.")
        if session.walk_mode != "group":
            raise ValueError("Only group walks allow joining.")
        if session.member_count >= session.max_members:
            raise ValueError("This group is full.")

    # Check if already a participant
    existing = WalkSessionParticipant.objects.filter(
        walk_session=session,
        user=user,
    ).first()

    if existing:
        if existing.participant_status == "joined":
            raise ValueError("You are already in this group.")
        # Re-join if previously left or declined
        existing.participant_status = "joined"
        existing.left_at = None
        existing.save(update_fields=["participant_status", "left_at", "updated_at"])
        return existing

    # Check if user already has another active walk
    active_walk = WalkSession.objects.filter(
        participants__user=user,
        participants__participant_status="joined",
        status__in=["pending", "active"],
    ).exclude(id=session.id).first()

    if active_walk:
        raise ValueError("You already have an active walk session.")

    participant = WalkSessionParticipant.objects.create(
        walk_session=session,
        user=user,
        participant_role="member",
        participant_status="joined",
    )

    logger.info(
        "%s joined walk %s (now %d members)",
        user.email,
        session.id,
        session.member_count,
    )

    # Sync walk chat participants
    try:
        from chat.services import create_walk_chat
        create_walk_chat(session)
    except Exception as exc:
        logger.warning("Failed to sync walk chat: %s", exc)

    return participant


def leave_walk_session(session, user):
    """
    Leave a walk session.
    Creator cannot leave — they must cancel or end the walk.
    """
    from .models import WalkSessionParticipant

    try:
        participant = WalkSessionParticipant.objects.get(
            walk_session=session,
            user=user,
            participant_status="joined",
        )
    except WalkSessionParticipant.DoesNotExist:
        raise ValueError("You are not in this walk session.")

    if participant.participant_role == "creator":
        raise ValueError(
            "The creator cannot leave. Use 'end walk' or 'cancel' instead."
        )

    participant.participant_status = "left"
    participant.left_at = timezone.now()
    participant.save(update_fields=["participant_status", "left_at", "updated_at"])

    # Stop sharing for this user
    try:
        from tracking.services import toggle_sharing
        toggle_sharing(user, False)
    except ImportError:
        pass

    logger.info("%s left walk %s", user.email, session.id)
    return participant


# ────────────────────────────────────────────────────────
# START WALK
# ────────────────────────────────────────────────────────
def start_walk(session, started_by):
    """
    Start a pending group walk.
    Only the creator can start it.
    Turns on location sharing for all participants.
    """
    if session.status != "pending":
        raise ValueError("Only pending walks can be started.")

    if session.created_by != started_by:
        raise ValueError("Only the creator can start the walk.")

    if session.member_count < 1:
        raise ValueError("Walk must have at least one participant.")

    session.status = "active"
    session.started_at = timezone.now()
    session.save(update_fields=["status", "started_at", "updated_at"])

    # Turn on sharing for all participants
    _toggle_participant_sharing(session, True)

    # Record starting locations
    _record_participant_locations(session)

    logger.info("Walk %s started by %s", session.id, started_by.email)

        # Ensure walk chat exists
    try:
        from chat.services import create_walk_chat
        create_walk_chat(session)
    except Exception as exc:
        logger.warning("Failed to ensure walk chat: %s", exc)

    return session


# ────────────────────────────────────────────────────────
# ARRIVE SAFELY
# ────────────────────────────────────────────────────────
def arrive_safely(session, user):
    """
    Mark that the user arrived safely at the destination.
    If the user is the creator or last active member, completes the walk.
    """
    if session.status != "active":
        raise ValueError("Walk is not active.")

    # Record final location
    _record_participant_locations(session)

    # Check if this should end the whole session
    # End if the creator arrives or if all members have left
    is_creator = session.created_by == user
    active_count = session.participants.filter(
        participant_status="joined",
    ).exclude(user=user).count()

    if is_creator or active_count == 0:
        session.status = "completed"
        session.arrived_safely = True
        session.ended_at = timezone.now()
        session.save(update_fields=[
            "status", "arrived_safely", "ended_at", "updated_at",
        ])

        _toggle_participant_sharing(session, False)

        logger.info("Walk %s completed — arrived safely", session.id)
    else:
        # Just mark this participant as left (they arrived)
        try:
            participant = session.participants.get(
                user=user,
                participant_status="joined",
            )
            participant.participant_status = "left"
            participant.left_at = timezone.now()
            participant.save(update_fields=["participant_status", "left_at", "updated_at"])
        except Exception:
            pass

        try:
            from tracking.services import toggle_sharing
            toggle_sharing(user, False)
        except ImportError:
            pass

        logger.info("%s arrived safely in walk %s", user.email, session.id)

    return session


# ────────────────────────────────────────────────────────
# END / CANCEL WALK
# ────────────────────────────────────────────────────────
def end_walk(session, ended_by):
    """
    End an active walk session.
    Only the creator can end it.
    """
    if session.status not in ("pending", "active"):
        raise ValueError("Walk is already ended or cancelled.")

    if session.created_by != ended_by:
        raise ValueError("Only the creator can end the walk.")

    now = timezone.now()
    session.status = "completed"
    session.ended_at = now
    session.save(update_fields=["status", "ended_at", "updated_at"])

    _toggle_participant_sharing(session, False)

    logger.info("Walk %s ended by %s", session.id, ended_by.email)
    return session


def cancel_walk(session, cancelled_by):
    """
    Cancel a walk session.
    Only the creator can cancel it.
    """
    if session.status not in ("pending", "active"):
        raise ValueError("Walk is already ended or cancelled.")

    if session.created_by != cancelled_by:
        raise ValueError("Only the creator can cancel the walk.")

    now = timezone.now()
    session.status = "cancelled"
    session.ended_at = now
    session.save(update_fields=["status", "ended_at", "updated_at"])

    _toggle_participant_sharing(session, False)

    logger.info("Walk %s cancelled by %s", session.id, cancelled_by.email)
    return session


# ────────────────────────────────────────────────────────
# QUERIES
# ────────────────────────────────────────────────────────
def get_active_groups(exclude_user=None):
    """
    Get all joinable group walks.
    Used by the Walk With Me modal "Active Groups" section.
    """
    from .models import WalkSession
    from django.db.models import F    # ← add this import inside the function

    queryset = WalkSession.objects.filter(
        walk_mode="group",
        status="pending",
    ).annotate(
        current_members=Count(
            "participants",
            filter=Q(participants__participant_status="joined"),
        ),
    ).select_related("created_by")

    queryset = queryset.filter(current_members__lt=F("max_members"))
    
    if exclude_user:
        # Exclude groups the user is already in
        queryset = queryset.exclude(
            participants__user=exclude_user,
            participants__participant_status="joined",
        )

    return queryset.order_by("-created_at")


def get_my_active_walk(user):
    """
    Get the user's current active/pending walk, if any.
    """
    from .models import WalkSession

    return WalkSession.objects.filter(
        participants__user=user,
        participants__participant_status="joined",
        status__in=["pending", "active"],
    ).select_related("created_by").first()


def get_walk_history(user):
    """
    Get a user's completed/cancelled walk history.
    Used by the Trips page.
    """
    from .models import WalkSession

    return WalkSession.objects.filter(
        participants__user=user,
    ).select_related("created_by").order_by("-created_at")


def get_dashboard_walk_stats():
    """
    Aggregated walk stats for the security dashboard.
    """
    from .models import WalkSession
    from datetime import timedelta

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active_walks = WalkSession.objects.filter(
        status="active",
    ).count()

    pending_groups = WalkSession.objects.filter(
        status="pending",
        walk_mode="group",
    ).count()

    completed_today = WalkSession.objects.filter(
        status="completed",
        ended_at__gte=today_start,
    ).count()

    total_arrived_safely = WalkSession.objects.filter(
        arrived_safely=True,
        ended_at__gte=today_start,
    ).count()

    security_escorts_active = WalkSession.objects.filter(
        status="active",
        walk_mode="security",
    ).count()

    return {
        "active_walks": active_walks,
        "pending_groups": pending_groups,
        "completed_today": completed_today,
        "arrived_safely_today": total_arrived_safely,
        "security_escorts_active": security_escorts_active,
    }