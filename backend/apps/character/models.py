# -*- coding: utf-8 -*-
"""Character Library and Gate 3 models (Phase 2D, Task 23).

The Character Library is the authoritative store of on-screen characters
(§20.1.4) reused across projects by a stable identity (§20.1.5, §42 "Character
ID"). Detected characters are extracted from an approved Script (Gate 2) and
must pass the six-step human review gate (Gate 3, §23.2) before they may be
used by the Scene Builder.

G-5 (identity preservation, §25): characters are rendered purely from stored
attributes; no generation step mutates identity without a recorded version
change, and a stable ``character_id`` yields consistent attributes across
every project that reuses it (CharacterLibrary).
"""
from django.conf import settings
from django.db import models


class Character(models.Model):
    """A project's detected character set and its Gate 3 state.

    Mirrors the Script artifact (Phase 2C): exactly one Character row per
    project (OneToOne). ``characters`` holds the structured list of detected
    characters with their attributes (age, gender, appearance, clothing,
    accessories, style). gate_state is the backend-owned Gate 3 state machine.
    """

    class GateState(models.TextChoices):
        DRAFT = "draft", "Draft"
        GENERATING = "generating", "Generating"
        REVIEW = "review", "Review"
        APPROVED = "approved", "Approved"
        REVISION_REQUESTED = "revision_requested", "Revision Requested"

    _TRANSITIONS = {
        GateState.DRAFT: {GateState.GENERATING},
        GateState.GENERATING: {GateState.REVIEW},
        GateState.REVIEW: {GateState.APPROVED, GateState.REVISION_REQUESTED},
        GateState.APPROVED: set(),
        GateState.REVISION_REQUESTED: {GateState.GENERATING},
    }

    project = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="character_set"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="character_sets"
    )
    script = models.ForeignKey(
        "script.Script",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="character_sets",
        help_text="The approved Script this set was detected from (Gate 2).",
    )

    # Detected/defined characters. Each entry is a dict:
    #   {"id": <stable_id>, "name": ..., "age": ..., "gender": ...,
    #    "appearance": {...}, "clothing": {...}, "accessories": {...},
    #    "style": {...}}
    characters = models.JSONField(default=list, blank=True)

    # Gate 3 state machine.
    gate_state = models.CharField(
        max_length=32, choices=GateState.choices, default=GateState.DRAFT
    )
    approval_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_characters",
    )
    approval_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    version = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["team", "gate_state"]),
            models.Index(fields=["project", "gate_state"]),
        ]

    def __str__(self):
        return f"CharacterSet #{self.id} ({self.project_id}) - {self.gate_state}"

    def can_transition(self, target):
        return target in self._TRANSITIONS.get(self.gate_state, set())

    def transition_to(self, target):
        """Validate a Gate 3 transition and mutate gate_state in-memory."""
        if not self.can_transition(target):
            raise ValueError(
                f"Cannot transition from {self.gate_state!r} to {target!r}"
            )
        self.gate_state = target


class CharacterLibrary(models.Model):
    """Persistent, versioned library of characters keyed by a stable identity.

    Fulfils §20.1.5 (character reuse) and G-5 (identity preservation). A
    character's attributes (age, gender, appearance, clothing, accessories,
    style) are stored once per ``character_id`` and are reused verbatim by
    every project, so the same ID yields consistent attributes everywhere.
    Editing a library character creates a new ``version`` under the same id.
    """

    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="character_library"
    )
    origin_project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_entries",
        help_text="Project where this character was first detected.",
    )
    character_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    age = models.CharField(max_length=64, blank=True, default="")
    gender = models.CharField(max_length=64, blank=True, default="")
    appearance = models.JSONField(default=dict, blank=True)
    clothing = models.JSONField(default=dict, blank=True)
    accessories = models.JSONField(default=list, blank=True)
    style = models.JSONField(default=dict, blank=True)

    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["character_id", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "character_id", "version"],
                name="unique_library_character_version",
            )
        ]
        indexes = [
            models.Index(fields=["team", "character_id"]),
        ]

    def __str__(self):
        return f"Library char {self.character_id} v{self.version} ({self.team_id})"


def current_library_version(team, character_id):
    """Return the highest version, or 0 when the character is not in the library."""
    latest = (
        CharacterLibrary.objects.filter(team=team, character_id=character_id)
        .order_by("-version")
        .first()
    )
    return latest.version if latest else 0


def can_generate_characters(character_set):
    """Gate 2 dependency helper: no character detection until the Script is approved.

    Mirrors research.can_generate_script (Gate 1 helper). Returns (ok, error).
    """
    from apps.script.models import Script

    if character_set.script is None or character_set.script_id is None:
        return False, "Script must exist and be approved before character detection"
    script = (
        Script.objects.filter(pk=character_set.script_id)
        .select_related("project")
        .first()
    )
    if not script:
        return False, "Script must exist and be approved before character detection"
    if script.gate_state != Script.GateState.APPROVED:
        return False, "Script must be approved before character detection"
    return True, ""
