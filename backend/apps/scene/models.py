# -*- coding: utf-8 -*-
"""Scene Builder and Gate 4 models (Phase 2E, Task 24 / Overview §20.1.6).

The Scene Builder assembles and configures the video scene by scene: it maps
scenes from the approved Script (Gate 2), assigns library characters (Gate 3,
stable IDs), visuals, and narration per scene, and sets order, pacing, and
transitions. The assembled scene package must pass the six-step human review
gate (Gate 4, §23.2) before video assembly / scene media production (§20.1.7).

Task 24 is a synchronous, deterministic scene *mapping* step over already
approved artifacts (approved Script + approved Character Library). It does not
run an AI generation job, so it intentionally does not use the Phase 2A
AsyncJob substrate and does not register an executor. The frozen Phase 2A
AsyncJob.JobType enum has no Task 24 job type (SCENE_MEDIA_GENERATION belongs to
Task 25, REGENERATION to Task 26); no modification is made to that frozen
contract here.

G-4/G-5 (identity preservation, §25): scenes reference characters purely by
their stable library ``character_id``, so the same ID renders the same character
across every scene and every project (G-5). Regeneration stays scoped to the
changed scene (G-4) because each scene carries a stable ``id``.
"""
from django.conf import settings
from django.db import models


class SceneBuilder(models.Model):
    """A project's assembled scene package and its Gate 4 state.

    There is exactly one SceneBuilder row per project (OneToOne). ``scenes``
    holds the structured list of mapped scene artifacts, each carrying a stable
    ``id``, its order, narration, visual direction, assigned character ids,
    pacing, transition, and metadata. gate_state is the backend-owned Gate 4
    state machine.
    """

    class GateState(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        APPROVED = "approved", "Approved"
        REVISION_REQUESTED = "revision_requested", "Revision Requested"

    _TRANSITIONS = {
        GateState.DRAFT: {GateState.REVIEW},
        GateState.REVIEW: {GateState.APPROVED, GateState.REVISION_REQUESTED},
        GateState.APPROVED: set(),
        GateState.REVISION_REQUESTED: {GateState.REVIEW},
    }

    project = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="scene_builder"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="scene_builders"
    )
    script = models.ForeignKey(
        "script.Script",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scene_builders",
        help_text="The approved Script package (Gate 2) this scene package maps.",
    )
    character_set = models.ForeignKey(
        "character.Character",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scene_builders",
        help_text="The approved Character set (Gate 3) whose characters are assigned.",
    )

    # Assembled scene package. Each entry is a dict:
    #   {"id": <stable_scene_id>, "order": <int>, "heading": ..., "narration": ...,
    #    "visual_direction": ..., "characters": [<stable_character_ids>],
    #    "pacing": ..., "transition": ..., "duration_seconds": <int>,
    #    "metadata": {...}}
    scenes = models.JSONField(default=list, blank=True)

    # Gate 4 state machine.
    gate_state = models.CharField(
        max_length=32, choices=GateState.choices, default=GateState.DRAFT
    )
    approval_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_scene_builders",
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
        return f"SceneBuilder #{self.id} ({self.project_id}) - {self.gate_state}"

    def can_transition(self, target):
        return target in self._TRANSITIONS.get(self.gate_state, set())

    def transition_to(self, target):
        """Validate a Gate 4 transition and mutate gate_state in-memory."""
        if not self.can_transition(target):
            raise ValueError(
                f"Cannot transition from {self.gate_state!r} to {target!r}"
            )
        self.gate_state = target


def can_build_scenes(builder):
    """Gate chain dependency helper: no scene building until Gate 2 + Gate 3 pass.

    Scene building (Gate 4) requires an approved Script (Gate 2) *and* an
    approved Character set (Gate 3): "approved Script + approved Character
    Library → Scene Builder → Gate 4" (§20.1.6, roadmap task 24; the four-gate
    chain §22.3.2). Returns (ok, error).
    """
    from apps.character.models import Character
    from apps.script.models import Script

    if builder.script is None or builder.script_id is None:
        return False, "Script must be approved before building scenes"
    script = Script.objects.filter(pk=builder.script_id).first()
    if not script:
        return False, "Script must be approved before building scenes"
    if script.gate_state != Script.GateState.APPROVED:
        return False, "Script must be approved before building scenes"

    if builder.character_set is None or builder.character_set_id is None:
        return False, "Characters must be approved before building scenes"
    character_set = Character.objects.filter(pk=builder.character_set_id).first()
    if not character_set:
        return False, "Characters must be approved before building scenes"
    if character_set.gate_state != Character.GateState.APPROVED:
        return False, "Characters must be approved before building scenes"
    if not character_set.characters:
        return False, "Characters must be approved before building scenes"
    return True, ""
