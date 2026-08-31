# -*- coding: utf-8 -*-
"""Analytics service layer (Task 43).

Boundary invariant: analytics never measures un-published content.
All queries filter by entry status == PUBLISHED.
"""
from django.db.models import Sum, Avg, Count


def record_published_performance(entry, views=0, likes=0, comments=0, shares=0, topic=""):
    """Record performance metrics for a published entry.

    Boundary: entry MUST be in PUBLISHED status.
    """
    from apps.publishing.models import ScheduledEntry
    from apps.analytics.models import PublishedPerformance

    if entry.status != ScheduledEntry.Status.PUBLISHED:
        raise ValueError("analytics only tracks published entries")

    total_interactions = likes + comments + shares
    engagement_rate = (total_interactions / views * 100) if views > 0 else 0.0

    obj, created = PublishedPerformance.objects.update_or_create(
        entry=entry,
        platform=entry.platform,
        defaults={
            "team": entry.team,
            "topic": topic,
            "views": views,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "engagement_rate": round(engagement_rate, 2),
        },
    )
    return obj


def get_analytics_summary(user, team_id=None):
    """Get aggregated analytics for a user's team(s).

    Only published entries are included.
    """
    from apps.analytics.models import PublishedPerformance

    team_ids = user.memberships.values_list("team_id", flat=True)
    qs = PublishedPerformance.objects.filter(team_id__in=team_ids)

    if team_id and int(team_id) in team_ids:
        qs = qs.filter(team_id=team_id)

    return qs.aggregate(
        total_views=Sum("views"),
        total_likes=Sum("likes"),
        total_comments=Sum("comments"),
        total_shares=Sum("shares"),
        avg_engagement=Avg("engagement_rate"),
        entry_count=Count("id", distinct=True),
    )


def get_analytics_by_platform(user, team_id=None):
    """Get analytics grouped by platform."""
    from apps.analytics.models import PublishedPerformance

    team_ids = user.memberships.values_list("team_id", flat=True)
    qs = PublishedPerformance.objects.filter(team_id__in=team_ids)

    if team_id and int(team_id) in team_ids:
        qs = qs.filter(team_id=team_id)

    return qs.values("platform").annotate(
        total_views=Sum("views"),
        total_likes=Sum("likes"),
        total_comments=Sum("comments"),
        total_shares=Sum("shares"),
        avg_engagement=Avg("engagement_rate"),
        entry_count=Count("id", distinct=True),
    ).order_by("-total_views")


def get_analytics_by_topic(user, team_id=None):
    """Get analytics grouped by topic."""
    from apps.analytics.models import PublishedPerformance

    team_ids = user.memberships.values_list("team_id", flat=True)
    qs = PublishedPerformance.objects.filter(team_id__in=team_ids).exclude(topic="")

    if team_id and int(team_id) in team_ids:
        qs = qs.filter(team_id=team_id)

    return qs.values("topic").annotate(
        total_views=Sum("views"),
        total_likes=Sum("likes"),
        avg_engagement=Avg("engagement_rate"),
        entry_count=Count("id", distinct=True),
    ).order_by("-total_views")


def export_audit_log(user, fmt="csv"):
    """Export audit logs for the user's teams.

    Returns the export record with record_count.
    """
    from apps.audit.models import AuditLog
    from apps.analytics.models import AuditExport
    from apps.projects.models import Project

    team_ids = user.memberships.values_list("team_id", flat=True)
    project_ids = Project.objects.filter(team_id__in=team_ids).values_list("id", flat=True)
    str_project_ids = [str(pid) for pid in project_ids]

    from django.db.models import Q
    qs = AuditLog.objects.filter(
        Q(target_type="project", target_id__in=str_project_ids) | Q(actor_id=user.id)
    ).order_by("-created_at")

    record_count = qs.count()

    export = AuditExport.objects.create(
        team=user.memberships.first().team if user.memberships.exists() else None,
        requested_by=user,
        format=fmt,
        record_count=record_count,
    )

    return export, qs
