# -*- coding: utf-8 -*-
"""Script package and Gate 2 models (Development Plan Day 22 / Overview §20.1.3).

Implements the Gate 2 artifact: a complete, production-ready script package
(title, outline, script, narration, scenes, captions, hashtags) generated from
approved Research (G-1: no writing before research approval; §22.3.1).

The Script row carries the Gate 2 state machine mirroring the Phase 2B Gate 1
pattern established by apps.research:

    draft -> generating -> review -> approved / revision_requested -> generating

Gate 2 must be approved before scene production (G-2: every script is reviewed;
§22.3.2: no production before script approval).
"""
from django.conf import settings
from django.db import models


class Script(models.Model):
    """A single project's script package and its Gate 2 state.

    There is exactly one Script row per project (OneToOne). gate_state is the
    backend-owned Gate 2 state machine; every transition is validated here
    before persisting.
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
        "projects.Project", on_delete=models.CASCADE, related_name="script"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="scripts"
    )
    research = models.ForeignKey(
        "research.Research",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="script",
    )

    # Script package fields (Overview §20.1.3 / Glossary "Script package").
    title = models.CharField(max_length=512, blank=True, default="")
    outline = models.TextField(blank=True, default="")
    script = models.TextField(blank=True, default="")
    narration = models.TextField(blank=True, default="")
    scenes = models.JSONField(default=list, blank=True)
    captions = models.JSONField(default=list, blank=True)
    hashtags = models.JSONField(default=list, blank=True)

    # Gate 2 state machine.
    gate_state = models.CharField(
        max_length=32, choices=GateState.choices, default=GateState.DRAFT
    )
    approval_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_scripts",
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
        return f"Script #{self.id} ({self.project_id}) - {self.gate_state}"

    def can_transition(self, target):
        return target in self._TRANSITIONS.get(self.gate_state, set())

    def transition_to(self, target):
        """Validate a Gate 2 transition and mutate gate_state in-memory."""
        if not self.can_transition(target):
            raise ValueError(
                f"Cannot transition from {self.gate_state!r} to {target!r}"
            )
        self.gate_state = target
