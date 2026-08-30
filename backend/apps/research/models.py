# -*- coding: utf-8 -*-
"""Research engine models (Development Plan Day 21).

Implements Gate 1 artifacts: the Research summary, its cited sources, and the
gap/contradiction flags surfaced to the user (invariant G-2: contradictions are
surfaced, never silently resolved). The Research row carries the Gate 1 state
machine (step25/17_STATE-MACHINE-GATES.md): draft -> generating -> review ->
approved / revision_requested -> generating.

G-1 (fact-grounding) is enforced by the project lifecycle state machine and by
downstream stage gates; this model stores the state the gates consult.
"""
from django.conf import settings
from django.db import models

from apps.core.enums import ProjectLifecycle


class Research(models.Model):
    """A single project's research artifact and its Gate 1 state.

    There is exactly one Research row per project (OneToOne). The gate_state
    field is the backend-owned Gate 1 state machine; every transition is
    validated here before persisting.
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
        "projects.Project", on_delete=models.CASCADE, related_name="research"
    )
    team = models.ForeignKey(
        "accounts.Team", on_delete=models.CASCADE, related_name="research"
    )
    summary = models.TextField(blank=True, default="")
    raw_output = models.JSONField(default=dict, blank=True)
    gate_state = models.CharField(
        max_length=32, choices=GateState.choices, default=GateState.DRAFT
    )
    approval_actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_research",
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
        return f"Research #{self.id} ({self.project_id}) - {self.gate_state}"

    def can_transition(self, target):
        return target in self._TRANSITIONS.get(self.gate_state, set())

    def transition_to(self, target):
        """Validate a Gate 1 transition and mutate gate_state in-memory."""
        if not self.can_transition(target):
            raise ValueError(
                f"Cannot transition from {self.gate_state!r} to {target!r}"
            )
        self.gate_state = target


class ResearchSource(models.Model):
    """A cited source attached to a Research artifact.

    Every claim in the summary is expected to map to at least one ResearchSource
    (test requirement "source citation"). Sources are team-scoped through their
    parent Research -> Project -> team.
    """

    research = models.ForeignKey(
        Research, on_delete=models.CASCADE, related_name="sources"
    )
    url = models.URLField(max_length=500)
    title = models.CharField(max_length=255, blank=True, default="")
    snippet = models.TextField(blank=True, default="")
    credibility_score = models.FloatField(default=0.0)
    accessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-credibility_score", "id"]
        indexes = [models.Index(fields=["research"])]

    def __str__(self):
        return f"Source {self.id} - {self.title or self.url}"


class ResearchGap(models.Model):
    """A flagged gap or contradiction surfaced during research (invariant G-2).

    Contradictions are recorded here and surfaced to the user rather than being
    silently resolved by the engine.
    """

    class GapType(models.TextChoices):
        GAP = "gap", "Gap"
        CONTRADICTION = "contradiction", "Contradiction"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    research = models.ForeignKey(
        Research, on_delete=models.CASCADE, related_name="gaps"
    )
    gap_type = models.CharField(
        max_length=24, choices=GapType.choices, default=GapType.GAP
    )
    description = models.TextField()
    source_a = models.TextField(blank=True, default="")
    source_b = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["research", "gap_type"])]

    def __str__(self):
        return f"{self.gap_type} #{self.id}"


def can_generate_script(project):
    """Invariant G-1 helper: no writing stage until research is approved.

    Returns (ok, error_message). Used by the script generation gate (Phase 2C)
    and available here so the Gate 1 contract is testable from Phase 2B.
    """
    research = Research.objects.filter(project=project).first()
    if not research or research.gate_state != Research.GateState.APPROVED:
        return False, "Research must be approved before script generation"
    return True, ""


def project_in_draft(project):
    """Return True when a project's lifecycle permits starting research (G-1)."""
    return project.lifecycle_state == ProjectLifecycle.DRAFT.value
