"""
Business logic for issue reports.
"""

import logging
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

logger = logging.getLogger(__name__)


def create_report(user, title, description, category="general", **kwargs):
    """
    Create a new issue report.
    Called when student taps "Report Issue" in QuickActionChips.
    """
    from .models import IssueReport

    report = IssueReport.objects.create(
        reported_by=user,
        title=title,
        description=description,
        category=category,
        priority=kwargs.get("priority", "medium"),
        latitude=kwargs.get("latitude"),
        longitude=kwargs.get("longitude"),
        location_text=kwargs.get("location_text", ""),
        photo=kwargs.get("photo"),
    )

    # Notify admin about new report
    try:
        from notifications.services import notify_admins
        notify_admins(
            title=f"New Issue Report: {title}",
            message=f"{user.full_name} reported: {description[:100]}",
            notification_type="system",
            data={
                "report_id": str(report.id),
                "category": category,
            },
        )
    except ImportError:
        pass

    logger.info(
        "Issue report created: %s by %s [%s]",
        report.id,
        user.email,
        category,
    )

    return report


def update_report_status(report, new_status, actor_user, admin_notes=""):
    """
    Update a report's status.
    Valid transitions:
      open → in_progress, resolved, dismissed
      in_progress → resolved, dismissed, open
      resolved → open (reopen)
      dismissed → open (reopen)
    """
    from .models import IssueReport, ReportComment

    old_status = report.status
    report.status = new_status

    if admin_notes:
        report.admin_notes = admin_notes

    update_fields = ["status", "admin_notes", "updated_at"]

    if new_status in ("resolved", "dismissed"):
        report.resolved_by = actor_user
        report.resolved_at = timezone.now()
        update_fields += ["resolved_by", "resolved_at"]
    elif new_status == "open" and old_status in ("resolved", "dismissed"):
        # Reopening
        report.resolved_by = None
        report.resolved_at = None
        update_fields += ["resolved_by", "resolved_at"]

    report.save(update_fields=update_fields)

    # Add system comment about status change
    ReportComment.objects.create(
        report=report,
        author=actor_user,
        comment_text=f"Status changed: {old_status} → {new_status}. {admin_notes}".strip(),
        is_internal=True,
    )

    # Notify the reporter
    try:
        from notifications.services import notify_user

        status_messages = {
            "in_progress": "Your report is being reviewed.",
            "resolved": "Your report has been resolved.",
            "dismissed": "Your report has been reviewed and dismissed.",
            "open": "Your report has been reopened.",
        }

        notify_user(
            user=report.reported_by,
            notification_type="system",
            title=f"Report Update: {report.title}",
            message=status_messages.get(new_status, f"Status updated to {new_status}."),
            data={"report_id": str(report.id), "new_status": new_status},
        )
    except ImportError:
        pass

    logger.info(
        "Report %s status: %s → %s by %s",
        report.id,
        old_status,
        new_status,
        actor_user.email,
    )

    return report


def assign_report(report, assigned_to, assigned_by):
    """Assign a report to a security officer or admin."""
    from .models import ReportComment

    report.assigned_to = assigned_to
    report.save(update_fields=["assigned_to", "updated_at"])

    if report.status == "open":
        report.status = "in_progress"
        report.save(update_fields=["status", "updated_at"])

    ReportComment.objects.create(
        report=report,
        author=assigned_by,
        comment_text=f"Assigned to {assigned_to.full_name}.",
        is_internal=True,
    )

    # Notify the assigned person
    try:
        from notifications.services import notify_user
        notify_user(
            user=assigned_to,
            notification_type="system",
            title=f"Report Assigned: {report.title}",
            message=f"You have been assigned to handle this report.",
            data={"report_id": str(report.id)},
        )
    except ImportError:
        pass

    logger.info(
        "Report %s assigned to %s by %s",
        report.id,
        assigned_to.email,
        assigned_by.email,
    )

    return report


def add_comment(report, author, comment_text, is_internal=False):
    """Add a comment to a report."""
    from .models import ReportComment

    comment = ReportComment.objects.create(
        report=report,
        author=author,
        comment_text=comment_text,
        is_internal=is_internal,
    )

    # Notify the other party
    try:
        from notifications.services import notify_user

        if author == report.reported_by:
            # Student commented — notify assigned admin
            if report.assigned_to:
                notify_user(
                    user=report.assigned_to,
                    notification_type="system",
                    title=f"New comment on: {report.title}",
                    message=comment_text[:100],
                    data={"report_id": str(report.id)},
                )
        else:
            # Admin commented — notify reporter
            if not is_internal:
                notify_user(
                    user=report.reported_by,
                    notification_type="system",
                    title=f"Update on your report: {report.title}",
                    message=comment_text[:100],
                    data={"report_id": str(report.id)},
                )
    except ImportError:
        pass

    return comment


def get_report_stats():
    """
    Aggregated report stats for the dashboard.
    """
    from .models import IssueReport

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_open = IssueReport.objects.filter(status="open").count()
    total_in_progress = IssueReport.objects.filter(status="in_progress").count()
    resolved_today = IssueReport.objects.filter(
        status="resolved",
        resolved_at__gte=today_start,
    ).count()
    resolved_this_week = IssueReport.objects.filter(
        status="resolved",
        resolved_at__gte=week_ago,
    ).count()
    new_today = IssueReport.objects.filter(
        created_at__gte=today_start,
    ).count()
    new_this_week = IssueReport.objects.filter(
        created_at__gte=week_ago,
    ).count()

    by_category = dict(
        IssueReport.objects.filter(
            status__in=["open", "in_progress"],
        ).values_list("category").annotate(
            count=Count("id"),
        ).order_by("-count")
    )

    by_priority = dict(
        IssueReport.objects.filter(
            status__in=["open", "in_progress"],
        ).values_list("priority").annotate(
            count=Count("id"),
        )
    )

    return {
        "open": total_open,
        "in_progress": total_in_progress,
        "total_active": total_open + total_in_progress,
        "resolved_today": resolved_today,
        "resolved_this_week": resolved_this_week,
        "new_today": new_today,
        "new_this_week": new_this_week,
        "by_category": by_category,
        "by_priority": by_priority,
    }