# -*- coding: utf-8 -*-
"""Thumbnail generation model (Backend Phase 3, Task 36 / Overview section 20.1.11).

The ThumbnailAsset stores a generated thumbnail: key scene visuals with title
text, produced at platform-specific dimensions with variations.
"""
from django.db import models


class ThumbnailAsset(models.Model):
    """A generated thumbnail for a project, scoped to a platform.

    One row per (project, platform_target) pair. Variations are stored
    as a JSON list of asset references.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    # Provenance
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="thumbnails"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="thumbnails"
    )
    scene_builder = models.ForeignKey(
        "scene.SceneBuilder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="thumbnails",
        help_text="The approved Scene Builder package this thumbnail derives from.",
    )

    # Platform target
    platform_target = models.CharField(max_length=64, blank=True, default="")
    width = models.PositiveIntegerField(default=1280)
    height = models.PositiveIntegerField(default=720)

    # Status
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    asset_ref = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    provider_metadata = models.JSONField(default=dict, blank=True)

    # Thumbnail metadata
    title_text = models.CharField(max_length=512, blank=True, default="")
    variations = models.JSONField(default=list, blank=True)
    version = models.PositiveIntegerField(default=1)

    # Error handling
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "platform_target"],
                name="uniq_thumbnail_project_platform",
            )
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self):
        return f"Thumbnail #{self.id} ({self.project_id}) - {self.platform_target} - {self.status}"
