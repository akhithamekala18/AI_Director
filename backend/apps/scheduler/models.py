# -*- coding: utf-8 -*-
"""Scheduler model (Backend Phase 3, Task 38 / Overview section 20.3.1).

ScheduleEntry stores per-platform scheduling with:
- Explicit date/time with timezone
- UTC normalization
- Preview-before-schedule invariant enforcement
- Reschedule/cancel support
- Best-time guidance
- Reminders tied to production state

One entry per (project, platform) pair.
"""
from django.db import models


class ScheduleEntry(models.Model):
    """A per-platform schedule entry for a project.

    Each entry represents a scheduled publication for a specific platform.
    Timezone-aware: stores both local requested time and normalized UTC.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        RESCHEDULED = "rescheduled", "Rescheduled"
        CANCELLED = "cancelled", "Cancelled"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"

    # Provenance
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="schedule_entries"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="schedule_entries"
    )

    # Platform
    platform = models.CharField(
        max_length=64,
        help_text="Target platform (YouTube, TikTok, Instagram, etc.)",
    )

    # Scheduling
    scheduled_local_datetime = models.DateTimeField(
        help_text="User-requested local date/time for publication.",
    )
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text="IANA timezone identifier (e.g. Asia/Kolkata, America/New_York).",
    )
    scheduled_utc_datetime = models.DateTimeField(
        help_text="Normalized UTC datetime for scheduling.",
    )

    # Status
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )

    # Best-time guidance
    best_time_suggestion = models.JSONField(
        default=dict,
        blank=True,
        help_text="Deterministic best-time suggestion for this platform.",
    )

    # Reminders
    reminder_sent = models.BooleanField(
        default=False,
        help_text="Whether the pre-publish reminder has been sent.",
    )
    reminder_scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reminder should fire.",
    )

    # Audit
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)

    # Versioning for reschedule
    version = models.PositiveIntegerField(default=1)
    previous_scheduled_utc = models.DateTimeField(
        null=True, blank=True,
        help_text="Previous UTC time before reschedule.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_utc_datetime"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "platform"],
                name="uniq_schedule_project_platform",
            )
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["scheduled_utc_datetime", "status"]),
            models.Index(fields=["status", "reminder_sent"]),
        ]

    def __str__(self):
        return (
            f"Schedule #{self.id} ({self.project_id}) - "
            f"{self.platform} - {self.scheduled_utc_datetime} - {self.status}"
        )
