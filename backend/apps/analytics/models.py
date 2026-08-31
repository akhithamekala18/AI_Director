# -*- coding: utf-8 -*-
from django.db import models


class PublishedPerformance(models.Model):
    """Published-performance tracking (Overview D20.4.1, Task 43).

    Sourced from published events only. Analytics never measures
    un-published content (boundary invariant).
    """
    entry = models.ForeignKey(
        "publishing.ScheduledEntry",
        on_delete=models.CASCADE,
        related_name="analytics",
    )
    team = models.ForeignKey(
        "accounts.Team",
        on_delete=models.CASCADE,
        related_name="analytics",
    )
    platform = models.CharField(max_length=64)
    topic = models.CharField(max_length=128, blank=True, default="")
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-recorded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "platform"],
                name="uniq_analytics_entry_platform",
            )
        ]

    def __str__(self):
        return f"Analytics: {self.platform} entry={self.entry_id} views={self.views}"


class AuditExport(models.Model):
    """Exportable audit report (Task 43, Overview D5.8)."""
    team = models.ForeignKey(
        "accounts.Team",
        on_delete=models.CASCADE,
        related_name="audit_exports",
    )
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="audit_exports",
    )
    format = models.CharField(
        max_length=16,
        choices=[("csv", "CSV"), ("json", "JSON")],
        default="csv",
    )
    record_count = models.PositiveIntegerField(default=0)
    file_path = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AuditExport #{self.id} ({self.format}) by {self.requested_by_id}"
