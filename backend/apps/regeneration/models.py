# -*- coding: utf-8 -*-
"""Regeneration / Editing models (Phase 2G, Task 26 / Overview §20.2.2, §26).

Task 26 is the editing/regeneration engine: scoped single-scene regeneration
with a deterministic blast radius, versioning and compare, and G-4 enforcement
(Development Plan Task 26, §44.2: "changing one scene regenerates that scene
and no other"; previous version comparable).

Models
------
* ``RegenerationRequest``: an orchestration record for one regeneration run.
  It targets a single scene of an approved Scene Builder package (Gate 4) and a
  set of media types, or the whole package when ``full`` is explicitly set.
  Its own status state machine (pending -> running -> completed / failed) is
  driven by the frozen Phase 2A AsyncJob (JobType.REGENERATION) executor.

* ``SceneMediaVersion``: an immutable snapshot of a ``SceneMedia`` row captured
  *before* regeneration, so the previous version remains comparable (§20.2.2
  "compare versions"). It records which media row/scene/type it belongs to,
  the prior version number, and a copy of the media fields.

No frozen Phase 1/2A-2F code is modified; regeneration reuses the frozen
`apps.scene_media.SceneMedia` (updated in place like its own `_update_media`
does) and the frozen `apps.scene_media.providers` abstraction for provider
independence. Credentials are never stored here.
"""
from django.db import models

from apps.scene_media.models import SceneMedia


class RegenerationRequest(models.Model):
    """A regeneration orchestration record for a project's approved scenes.

    Regeneration always operates on existing media produced by Task 25
    (SceneMedia rows) of an APPROVED Scene Builder package (Gate 4). By default
    it is scoped to a single scene (G-4); "full" regeneration is only allowed
    when explicitly requested.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    _TRANSITIONS = {
        Status.PENDING: {Status.RUNNING, Status.FAILED},
        Status.RUNNING: {Status.COMPLETED, Status.FAILED},
        Status.COMPLETED: set(),
        Status.FAILED: set(),
    }

    # Ownership / provenance
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="regeneration_requests",
    )
    team = models.ForeignKey(
        "accounts.Team",
        on_delete=models.CASCADE,
        related_name="regeneration_requests",
        help_text="Bound to the project's team; every query is team-scoped.",
    )
    scene_builder = models.ForeignKey(
        "scene.SceneBuilder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="regeneration_requests",
        help_text="The approved Scene Builder package (Gate 4) being edited.",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="regeneration_requests",
        help_text="The user who requested the regeneration.",
    )

    # Scoping (G-4: single scene by default, full only when explicit)
    scene_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="The stable scene id to regenerate (empty only for full).",
    )
    media_types = models.JSONField(default=list, blank=True)
    full = models.BooleanField(
        default=False,
        help_text="True only when the user explicitly requests full regeneration.",
    )

    # Status / results
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    async_job = models.ForeignKey(
        "ai_orchestration.AsyncJob",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="regeneration_requests",
    )
    media_snapshot_version = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["scene_builder", "scene_id"]),
        ]

    def __str__(self):
        scope = "full" if self.full else self.scene_id or "?"
        return f"Regen #{self.id} ({scope}) - {self.status}"

    def can_transition(self, target_status):
        return target_status in self._TRANSITIONS.get(self.status, set())

    def transition_to(self, target_status):
        if not self.can_transition(target_status):
            raise ValueError(
                f"Cannot transition from {self.status!r} to {target_status!r}"
            )
        self.status = target_status


class SceneMediaVersion(models.Model):
    """Immutable snapshot of a SceneMedia row before regeneration.

    Preserves the *previous* version of a media asset so it stays comparable
    (§20.2.2 "compare versions"; Task 26 exit "previous version comparable").
    A new SceneMediaVersion row is appended each time that media row is
    regenerated.
    """

    media = models.ForeignKey(
        SceneMedia,
        on_delete=models.CASCADE,
        related_name="version_history",
    )
    regeneration = models.ForeignKey(
        RegenerationRequest,
        on_delete=models.CASCADE,
        related_name="snapshots",
        null=True,
        blank=True,
        help_text="The regeneration run that produced this snapshot.",
    )
    version = models.PositiveIntegerField(
        help_text="The media version number this snapshot represents."
    )
    media_type = models.CharField(max_length=16, choices=SceneMedia.MediaType.choices)
    scene_id = models.CharField(max_length=64)
    scene_order = models.PositiveIntegerField(default=0)
    asset_ref = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    provider_metadata = models.JSONField(default=dict, blank=True)
    direction = models.TextField(blank=True, default="")
    narration = models.TextField(blank=True, default="")
    characters = models.JSONField(default=list, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    pacing = models.CharField(max_length=32, blank=True, default="")
    transition = models.CharField(max_length=32, blank=True, default="")
    voice = models.JSONField(default=dict, blank=True)
    music = models.JSONField(default=dict, blank=True)
    caption = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["media", "-version"]
        indexes = [
            models.Index(fields=["media", "version"]),
            models.Index(fields=["scene_id", "media_type"]),
        ]

    def __str__(self):
        return f"{self.media_type}@{self.scene_id} v{self.version}"
