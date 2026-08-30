# -*- coding: utf-8 -*-
"""Scene Media Generation models (Phase 2F, Task 25 / Overview §20.1.8–20.1.10).

Task 25 produces per-scene media assets — visual, voice/narration, music/audio,
and subtitles/captions — scoped by the *approved* Scene Builder package (Gate 4).
Each approved scene yields one asset per media type, tied to its stable scene ID
(exit test: "Each approved scene produces visual/voice/music/subtitle assets
tied to scene ID").

Media generation runs asynchronously through the frozen Phase 2A AsyncJob
substrate using JobType.SCENE_MEDIA_GENERATION. This model persists the concrete
per-scene generated asset and its provider/status metadata. It never stores
provider credentials or secrets — only a provider name and opaque provider
metadata (G-9 cost/accounting stays on the AsyncJob).
"""
from django.db import models


class SceneMedia(models.Model):
    """A single generated media asset for one scene of an approved package.

    One row per (scene_builder, scene_id, media_type) pair. ``scene_id`` is the
    stable scene id from the approved Scene Builder package (G-5 identity), and
    ``scene_order`` preserves ordering (G-4: media stays scoped to its scene).
    """

    class MediaType(models.TextChoices):
        VISUAL = "visual", "Visual"
        VOICE = "voice", "Voice / Narration"
        MUSIC = "music", "Music / Audio"
        SUBTITLE = "subtitle", "Subtitle / Caption"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    # Provenance / ownership
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="scene_media"
    )
    team = models.ForeignKey(
        "accounts.Team",
        on_delete=models.CASCADE,
        related_name="scene_media",
        help_text="Bound to the project's team; every query is team-scoped.",
    )
    scene_builder = models.ForeignKey(
        "scene.SceneBuilder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="media",
        help_text="The approved Scene Builder package this media derives from.",
    )

    # Scene identity (G-5 stable scene ids from the approved package)
    scene_id = models.CharField(max_length=64)
    scene_order = models.PositiveIntegerField(default=0)

    # Media
    media_type = models.CharField(max_length=16, choices=MediaType.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    asset_ref = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=64, blank=True, default="")
    provider_metadata = models.JSONField(default=dict, blank=True)

    # Direction / prompt metadata (never provider credentials)
    direction = models.TextField(blank=True, default="")
    narration = models.TextField(blank=True, default="")
    characters = models.JSONField(default=list, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    pacing = models.CharField(max_length=32, blank=True, default="")
    transition = models.CharField(max_length=32, blank=True, default="")

    # Media-type specific detail
    voice = models.JSONField(default=dict, blank=True)
    music = models.JSONField(default=dict, blank=True)
    caption = models.JSONField(default=dict, blank=True)

    error_message = models.TextField(blank=True, default="")
    version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scene_order", "media_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["scene_builder", "scene_id", "media_type"],
                name="uniq_scene_media_builder_scene_type",
            )
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["project", "media_type"]),
            models.Index(fields=["scene_builder", "scene_id"]),
        ]

    def __str__(self):
        return f"{self.media_type}@{self.scene_id} ({self.status})"
