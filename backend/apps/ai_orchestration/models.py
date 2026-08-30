# -*- coding: utf-8 -*-
"""Async job tracking (Development Plan Day 20, §36.2, G-9).

Provides persistent job status for AI generation tasks with team isolation,
cost tracking, and retry support.
"""
from django.conf import settings
from django.db import models


class AsyncJob(models.Model):
    """Async job tracking for AI generation operations.

    Jobs are scoped to a team and project, owned by a user, and track
    status, progress, cost, and retry information. The job state machine
    enforces valid transitions only.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        RETRYING = "retrying", "Retrying"

    class JobType(models.TextChoices):
        RESEARCH_GENERATION = "research_generation", "Research Generation"
        SCRIPT_GENERATION = "script_generation", "Script Generation"
        CHARACTER_DETECTION = "character_detection", "Character Detection"
        SCENE_MEDIA_GENERATION = "scene_media_generation", "Scene Media Generation"
        REGENERATION = "regeneration", "Scene Regeneration"

    # Valid state transitions
    _TRANSITIONS = {
        Status.PENDING: {Status.RUNNING, Status.CANCELLED},
        Status.RUNNING: {Status.COMPLETED, Status.FAILED, Status.CANCELLED, Status.RETRYING},
        Status.RETRYING: {Status.RUNNING, Status.FAILED, Status.CANCELLED},
        Status.COMPLETED: set(),
        Status.FAILED: {Status.RETRYING, Status.CANCELLED},
        Status.CANCELLED: set(),
    }

    # Ownership
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="jobs"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="jobs"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs"
    )

    # Job metadata
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    progress = models.FloatField(default=0.0)

    # Result
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")

    # Retry
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)

    # Cost tracking (G-9)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    cost_currency = models.CharField(max_length=3, default="USD")

    # Provider
    provider = models.CharField(max_length=64, blank=True, default="")

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["job_type", "status"]),
        ]

    def __str__(self):
        return f"Job {self.id}: {self.job_type} ({self.status})"

    def can_transition(self, target_status):
        """Check if a transition to target_status is valid."""
        return target_status in self._TRANSITIONS.get(self.status, set())

    def transition_to(self, target_status):
        """Transition to target_status if valid, raising ValueError if not."""
        if not self.can_transition(target_status):
            raise ValueError(
                f"Cannot transition from {self.status!r} to {target_status!r}"
            )
        self.status = target_status
