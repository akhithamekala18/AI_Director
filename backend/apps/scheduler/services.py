# -*- coding: utf-8 -*-
"""Scheduler service layer (Task 38 / Overview section 20.3.1).

Responsibilities:
  * verify preview-before-schedule invariant server-side
  * verify project membership (team isolation)
  * create per-platform schedule entries with timezone normalization
  * reschedule entries
  * cancel entries
  * provide calendar dataset
  * provide best-time guidance
  * manage reminders tied to production state
  * audit schedule events

Team isolation: every query is scoped to user.memberships.
"""
import zoneinfo
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone as dj_tz

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from .models import ScheduleEntry


def _is_member(user, project):
    return user.memberships.filter(team_id=project.team_id).exists()


def _normalize_utc(local_dt, tz_name):
    """Convert a naive/local datetime to timezone-aware UTC."""
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except (KeyError, zoneinfo.ZoneInfoNotFoundError) as exc:
        raise DjangoValidationError(f"Invalid timezone: '{tz_name}'") from exc

    # If local_dt is naive, attach the timezone
    if dj_tz.is_naive(local_dt):
        aware_local = local_dt.replace(tzinfo=tz)
    else:
        # If already aware, convert to the specified timezone
        aware_local = local_dt.astimezone(tz)

    return aware_local.astimezone(zoneinfo.ZoneInfo("UTC")).replace(tzinfo=None)


def _get_best_time_suggestion(platform):
    """Deterministic best-time guidance for a platform.

    Based on common social media best-time norms (Overview section 20.3.1).
    Returns a dict with suggested hours and reasoning.
    """
    suggestions = {
        "YouTube": {
            "best_days": ["Thursday", "Friday", "Saturday"],
            "best_hours_utc": [14, 15, 16, 17, 18],
            "reasoning": "YouTube engagement peaks on Thu-Sat afternoons (UTC).",
        },
        "TikTok": {
            "best_days": ["Tuesday", "Thursday", "Friday"],
            "best_hours_utc": [10, 11, 12, 13, 14, 19, 20],
            "reasoning": "TikTok engagement peaks on weekday mornings and evenings.",
        },
        "Instagram": {
            "best_days": ["Monday", "Wednesday", "Friday"],
            "best_hours_utc": [11, 12, 13, 14, 17, 18, 19],
            "reasoning": "Instagram engagement peaks on weekday midday and evening.",
        },
        "Instagram Reels": {
            "best_days": ["Monday", "Wednesday", "Friday"],
            "best_hours_utc": [11, 12, 13, 14, 17, 18, 19],
            "reasoning": "Instagram Reels engagement peaks on weekday midday and evening.",
        },
        "Twitter": {
            "best_days": ["Monday", "Wednesday", "Friday"],
            "best_hours_utc": [12, 13, 14, 15, 16, 17],
            "reasoning": "Twitter engagement peaks on weekday midday.",
        },
        "LinkedIn": {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "best_hours_utc": [13, 14, 15, 16, 17],
            "reasoning": "LinkedIn engagement peaks on weekday business hours.",
        },
    }
    return suggestions.get(platform, {
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours_utc": [12, 13, 14, 15, 16],
        "reasoning": "General best-time guidance for this platform.",
    })


def _compute_reminder_time(scheduled_utc):
    """Compute reminder time: 1 hour before scheduled UTC time."""
    return scheduled_utc - timedelta(hours=1)


# --- CRUD Operations ---

def list_entries(user, project):
    """List schedule entries for a project with team isolation."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduleEntry.objects.filter(project=project, team_id__in=team_ids)


def get_entry(user, entry_id):
    """Fetch one schedule entry with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduleEntry.objects.filter(id=entry_id, team_id__in=team_ids).first()


def create_entry(user, project, platform, local_datetime_str, tz_name="UTC"):
    """Create a per-platform schedule entry.

    Validates:
      - team membership
      - preview-before-schedule invariant
      - timezone validity
      - no duplicate platform entry
    """
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")

    # Parse the local datetime
    try:
        if isinstance(local_datetime_str, str):
            local_dt = datetime.fromisoformat(local_datetime_str)
        else:
            local_dt = local_datetime_str
    except (ValueError, TypeError) as exc:
        raise DjangoValidationError("invalid datetime format") from exc

    # Normalize to UTC
    utc_dt = _normalize_utc(local_dt, tz_name)

    # Enforce preview-before-schedule invariant
    from apps.preview.services import has_approved_preview
    if not has_approved_preview(user, project, platform):
        raise DjangoValidationError(
            f"scheduling requires an approved preview for platform '{platform}'"
        )

    # Check for existing entry on this platform
    existing = ScheduleEntry.objects.filter(
        project=project, platform=platform
    ).first()
    if existing and existing.status != ScheduleEntry.Status.CANCELLED:
        raise DjangoValidationError(
            f"schedule entry already exists for platform '{platform}'"
        )

    # Get best-time suggestion
    best_time = _get_best_time_suggestion(platform)

    # Compute reminder time
    reminder_at = _compute_reminder_time(utc_dt)

    entry = ScheduleEntry.objects.create(
        project=project,
        team=project.team,
        platform=platform,
        scheduled_local_datetime=local_dt,
        timezone=tz_name,
        scheduled_utc_datetime=utc_dt,
        status=ScheduleEntry.Status.SCHEDULED,
        best_time_suggestion=best_time,
        reminder_scheduled_at=reminder_at,
        version=1,
    )

    record_audit(
        user,
        AuditAction.CREATE.value,
        "schedule_entry",
        entry.id,
        f"schedule_created_{platform}",
    )

    return entry


def reschedule_entry(user, entry, new_local_datetime_str, new_tz_name=None):
    """Reschedule an existing entry to a new date/time.

    Validates:
      - team membership
      - entry is in schedulable state
      - preview-before-schedule invariant still holds
      - timezone validity
    """
    if not _is_member(user, entry.project):
        raise DjangoValidationError("not a member of this project's team")

    if entry.status not in (
        ScheduleEntry.Status.SCHEDULED,
        ScheduleEntry.Status.RESCHEDULED,
    ):
        raise DjangoValidationError(
            f"cannot reschedule entry in '{entry.status}' state"
        )

    # Parse new datetime
    try:
        if isinstance(new_local_datetime_str, str):
            new_local_dt = datetime.fromisoformat(new_local_datetime_str)
        else:
            new_local_dt = new_local_datetime_str
    except (ValueError, TypeError) as exc:
        raise DjangoValidationError("invalid datetime format") from exc

    tz = new_tz_name or entry.timezone
    new_utc_dt = _normalize_utc(new_local_dt, tz)

    # Re-validate preview-before-schedule
    from apps.preview.services import has_approved_preview
    if not has_approved_preview(user, entry.project, entry.platform):
        raise DjangoValidationError(
            f"scheduling requires an approved preview for platform '{entry.platform}'"
        )

    # Store previous UTC for audit
    entry.previous_scheduled_utc = entry.scheduled_utc_datetime
    entry.scheduled_local_datetime = new_local_dt
    entry.timezone = tz
    entry.scheduled_utc_datetime = new_utc_dt
    entry.status = ScheduleEntry.Status.RESCHEDULED
    entry.version += 1
    entry.reminder_scheduled_at = _compute_reminder_time(new_utc_dt)
    entry.reminder_sent = False
    entry.save()

    record_audit(
        user,
        AuditAction.UPDATE.value,
        "schedule_entry",
        entry.id,
        f"schedule_rescheduled_{entry.platform}",
    )

    return entry




def cancel_entry(user, entry, reason=""):
    """Cancel a schedule entry.

    Validates:
      - team membership
      - entry is in cancellable state
    """
    if not _is_member(user, entry.project):
        raise DjangoValidationError("not a member of this project's team")

    if entry.status in (
        ScheduleEntry.Status.CANCELLED,
        ScheduleEntry.Status.PUBLISHED,
    ):
        raise DjangoValidationError(
            f"cannot cancel entry in '{entry.status}' state"
        )

    entry.status = ScheduleEntry.Status.CANCELLED
    entry.cancelled_at = dj_tz.now()
    entry.cancellation_reason = reason.strip() if reason else ""
    entry.save()

    record_audit(
        user,
        AuditAction.UPDATE.value,
        "schedule_entry",
        entry.id,
        f"schedule_cancelled_{entry.platform}",
    )

    return entry
def get_calendar_entries(user, project):
    """Get calendar dataset for a project.

    Returns all active (non-cancelled) entries sorted by UTC datetime.
    Suitable for rendering a content calendar.
    """
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduleEntry.objects.filter(
        project=project,
        team_id__in=team_ids,
    ).exclude(status=ScheduleEntry.Status.CANCELLED)


def get_best_time_suggestion(user, project, platform):
    """Get best-time guidance for a platform."""
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")
    return _get_best_time_suggestion(platform)


def get_pending_reminders(user, project):
    """Get entries that need reminders sent."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    now = dj_tz.now().replace(tzinfo=None)
    return ScheduleEntry.objects.filter(
        project=project,
        team_id__in=team_ids,
        reminder_sent=False,
        reminder_scheduled_at__lte=now,
        status__in=[
            ScheduleEntry.Status.SCHEDULED,
            ScheduleEntry.Status.RESCHEDULED,
        ],
    )
