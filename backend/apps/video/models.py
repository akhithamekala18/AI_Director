# -*- coding: utf-8 -*-
"""Video generation model (Backend Phase 3, Task 36 / Overview section 20.1.7).

The VideoAsset stores a generated video composite: scene visuals, narration,
captions, and music combined into a single video file. Each video is scoped
to an approved Scene Builder package (Gate 4) and a target platform.

Per-scene re-render is supported: regenerating a single scene produces a new
version of the video with only that scene's assets changed (G-4 scoped
regeneration).
"""
from django.db import models


class VideoAsset(models.Model):
    """A generated video for a project, scoped to a platform.

    One row per (project, platform_target) pair. The video is produced by
    compositing the approved scene package's media assets (visual, voice,
    music, subtitle) into a single rendered output.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    # Provenance
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="videos"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="videos"
    )
    scene_builder = models.ForeignKey(
        "scene.SceneBuilder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="videos",
        help_text="The approved Scene Builder package this video derives from.",
    )

    # Platform target
    platform_target = models.CharField(max_length=64, blank=True, default="")
    aspect_ratio = models.CharField(max_length=16, blank=True, default="9:16")
    resolution_width = models.PositiveIntegerField(default=1080)
    resolution_height = models.PositiveIntegerField(default=1920)

    # Status
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    asset_ref = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    provider_metadata = models.JSONField(default=dict, blank=True)

    # Video metadata
    duration_seconds = models.PositiveIntegerField(default=0)
    scene_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)

    # Error handling
    error_message = models.TextField(blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "platform_target"],
                name="uniq_video_project_platform",
            )
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self):
        return f"Video #{self.id} ({self.project_id}) - {self.platform_target} - {self.status}"
