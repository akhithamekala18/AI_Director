# -*- coding: utf-8 -*-
"""Research service layer and Gate 1 orchestration (Development Plan Day 21).

Encapsulates the Gate 1 state machine transitions (step25/17_STATE-MACHINE-GATES
and step24/09_RESEARCH-ENGINE-AUDIT):
  draft -> generating (project in DRAFT state)
  generating -> review (summary non-empty, >=1 source)  [done by the executor]
  review -> approved (>=1 source)
  review -> revision_requested (reason required)
  revision_requested -> generating (previous version preserved)

Generation runs through the Phase 2A AsyncJob substrate (job_type
research_generation) via `execute_job` + `register_executor`. Team isolation is
enforced by scoping every query to the user's memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from .models import Research, ResearchGap, ResearchSource, project_in_draft
from .tasks import enqueue_research_job


def get_research(user, project):
    """Return the project's Research with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return (
        Research.objects.filter(project=project, team_id__in=team_ids)
        .select_related("project")
        .first()
    )


def _create_or_get_research(user, project):
    research, created = Research.objects.get_or_create(
        project=project,
        defaults={"team": project.team},
    )
    return research


def generate_research(user, project):
    """Initiate research generation (Gate 1: draft/revision_requested -> generating).

    Creates the Research artifact if needed, validates the starting state,
    transitions to `generating`, records the audit event, and enqueues a
    Phase 2A AsyncJob (research_generation) to run the engine.

    Returns the created/updated Research.
    """
    research = _create_or_get_research(user, project)

    if research.gate_state == Research.GateState.APPROVED:
        raise DjangoValidationError("research is already approved")
    if research.gate_state == Research.GateState.REVIEW:
        raise DjangoValidationError("research is already generated and awaiting review")
    if research.gate_state == Research.GateState.GENERATING:
        raise DjangoValidationError("research generation is already in progress")

    regenerating = research.gate_state == Research.GateState.REVISION_REQUESTED

    if not regenerating:
        if not project_in_draft(project):
            raise DjangoValidationError(
                "research generation requires the project to be in Draft state"
            )
    else:
        # Previous version is preserved: the current summary/version stays in
        # place until the regenerated artifact replaces it (invariant).
        pass

    with transaction.atomic():
        research.transition_to(Research.GateState.GENERATING)
        research.save(update_fields=["gate_state", "updated_at"])
        action = (
            "research_regeneration_started"
            if regenerating
            else "research_generation_started"
        )
        record_audit(user, AuditAction.UPDATE.value, "research", research.id, action)
        enqueue_research_job(
            user=user,
            project=project,
            research=research,
            regenerate=regenerating,
        )

    # Reflect the authoritative state: in eager (test) mode the dispatched job
    # completes synchronously and moves the row to `review`; in production it
    # remains `generating` until the worker runs. Re-read to avoid returning a
    # stale in-memory value.
    research.refresh_from_db()
    return research


def approve_research(user, research):
    """Gate 1: review -> approved. Requires at least one source (G-1).

    Only callable from the `review` state. Persists the approval actor/time and
    records the audit event.
    """
    if research.gate_state != Research.GateState.REVIEW:
        raise DjangoValidationError(
            "research must be in review state before it can be approved"
        )
    if not research.sources.exists():
        raise DjangoValidationError(
            "research cannot be approved without at least one cited source"
        )
    with transaction.atomic():
        research.transition_to(Research.GateState.APPROVED)
        research.approval_actor = user
        research.approval_at = _now()
        research.save(
            update_fields=["gate_state", "approval_actor", "approval_at", "updated_at"]
        )
        record_audit(user, AuditAction.UPDATE.value, "research", research.id, "research_approved")
    return research


def request_research_changes(user, research, reason):
    """Gate 1: review -> revision_requested. A reason is required."""
    if research.gate_state != Research.GateState.REVIEW:
        raise DjangoValidationError(
            "research must be in review state to request changes"
        )
    if not reason or not reason.strip():
        raise DjangoValidationError("a rejection reason is required")
    with transaction.atomic():
        research.transition_to(Research.GateState.REVISION_REQUESTED)
        research.rejection_reason = reason.strip()
        research.save(update_fields=["gate_state", "rejection_reason", "updated_at"])
        record_audit(
            user,
            AuditAction.UPDATE.value,
            "research",
            research.id,
            "research_revision_requested",
        )
    return research


def research_sources(user, research):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ResearchSource.objects.filter(
        research=research, research__team_id__in=team_ids
    )


def research_gaps(user, research):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ResearchGap.objects.filter(
        research=research, research__team_id__in=team_ids
    )


def _now():
    from django.utils import timezone

    return timezone.now()
