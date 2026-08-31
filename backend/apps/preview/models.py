# -*- coding: utf-8 -*-
"""Preview rendering model (Backend Phase 3, Task 37 / Overview section 20.2.1).

The PreviewAsset stores a platform-accurate preview of a generated video.
A preview must exist and be approved BEFORE a video can be scheduled.

Invariant: schedule is blocked until an approved preview exists for the
entry's target platform.
"""
from django.db import models


class PreviewAsset(models.Model):
    """A platform-accurate preview for a video, scoped to a platform.

    One row per (project, platform_target) pair. The preview is produced
    by rendering the VideoAsset through a platform-accurate preview engine.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RENDERING = "rendering", "Rendering"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class ApprovalState(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    # Provenance
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="previews"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="previews"
    )
    video = models.ForeignKey(
        "video.VideoAsset",
        on_delete=models.CASCADE,
        related_name="previews",
        help_text="The VideoAsset this preview is derived from.",
    )
    scene_builder = models.ForeignKey(
        "scene.SceneBuilder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="previews",
        help_text="The approved Scene Builder package this preview derives from.",
    )

    # Platform target
    platform_target = models.CharField(max_length=64, blank=True, default="")
    aspect_ratio = models.CharField(max_length=16, blank=True, default="16:9")
    resolution_width = models.PositiveIntegerField(default=1920)
    resolution_height = models.PositiveIntegerField(default=1080)

    # Status
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    asset_ref = models.TextField(
        blank=True,
        default="",
        help_text="Reference to the rendered preview asset.",
    )
    provider = models.CharField(max_length=64, blank=True, default="")
    provider_metadata = models.JSONField(default=dict, blank=True)

    # Preview metadata
    duration_seconds = models.PositiveIntegerField(default=0)
    scene_count = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)

    # Approval
    approval_state = models.CharField(
        max_length=16,
        choices=ApprovalState.choices,
        default=ApprovalState.PENDING,
        help_text="Whether the preview has been reviewed and approved.",
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_previews",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    # Error handling
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "platform_target"],
                name="uniq_preview_project_platform",
            )
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "approval_state"]),
            models.Index(fields=["approval_state", "platform_target"]),
        ]

    def __str__(self):
        return (
            f"Preview #{self.id} ({self.project_id}) - "
            f"{self.platform_target} - {self.status} - {self.approval_state}"
        )

    @property
    def is_approved(self):
        return self.approval_state == self.ApprovalState.APPROVED
