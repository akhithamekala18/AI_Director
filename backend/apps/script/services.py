# -*- coding: utf-8 -*-
"""Script service layer and Gate 2 orchestration (Development Plan Day 22 /
Overview §20.1.3).

Encapsulates the Gate 2 state machine transitions (mirroring the Gate 1 pattern
from apps.research):

  draft -> generating  (G-1: approved research required)
  generating -> review  [done by the executor]
  review -> approved
  review -> revision_requested  (reason required)
  revision_requested -> generating  (previous version preserved)

Every script transition depends on the approved Research artifact (G-1: "no
writing before research approval", §22.3.1) via research.can_generate_script.
Generation runs through the Phase 2A AsyncJob substrate (job_type
script_generation) via execute_job + the script_generation executor. Team
isolation is enforced by scoping every query to the user's memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit
from apps.core.enums import AuditAction
from apps.research.models import Research, can_generate_script

from .models import Script
from .tasks import enqueue_script_job


def get_script(user, project):
    """Return the project's Script with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return (
        Script.objects.filter(project=project, team_id__in=team_ids)
        .select_related("project", "research")
        .first()
    )


def _get_approved_research(project):
    """Return the project's approved Research artifact (for provenance)."""
    return (
        Research.objects.filter(project=project)
        .order_by("-updated_at")
        .first()
    )


def _create_or_get_script(project, research):
    script, created = Script.objects.get_or_create(
        project=project,
        defaults={"team": project.team, "research": research},
    )
    return script


def generate_script(user, project):
    """Initiate script generation (Gate 2: draft/revision_requested -> generating).

    Enforces the G-1 invariant (approved research required) and the Gate 2
    starting-state prerequisites, transitions to `generating`, records the
    audit event, and enqueues a Phase 2A AsyncJob (script_generation) to run
    the engine.
    """
    research = _get_approved_research(project)
    script = _create_or_get_script(project, research)

    if script.gate_state == Script.GateState.APPROVED:
        raise DjangoValidationError("script is already approved")
    if script.gate_state == Script.GateState.REVIEW:
        raise DjangoValidationError("script is already generated and awaiting review")
    if script.gate_state == Script.GateState.GENERATING:
        raise DjangoValidationError("script generation is already in progress")

    regenerating = script.gate_state == Script.GateState.REVISION_REQUESTED

    ok, err = can_generate_script(project)
    if not ok:
        raise DjangoValidationError(err)

    with transaction.atomic():
        script.transition_to(Script.GateState.GENERATING)
        script.save(update_fields=["gate_state", "updated_at"])
        action = (
            "script_regeneration_started"
            if regenerating
            else "script_generation_started"
        )
        record_audit(user, AuditAction.UPDATE.value, "script", script.id, action)
        enqueue_script_job(user=user, project=project, script=script)

    script.refresh_from_db()
    return script


def approve_script(user, script):
    """Gate 2: review -> approved. Requires a non-empty script (G-2).

    Only callable from the `review` state. Persists the approval actor/time and
    records the audit event.
    """
    if script.gate_state != Script.GateState.REVIEW:
        raise DjangoValidationError(
            "script must be in review state before it can be approved"
        )
    if not script.script.strip():
        raise DjangoValidationError(
            "script cannot be approved without a generated script body"
        )
    if not script.title.strip():
        raise DjangoValidationError("script cannot be approved without a title")
    if not script.narration.strip():
        raise DjangoValidationError(
            "script cannot be approved without narration text"
        )
    with transaction.atomic():
        script.transition_to(Script.GateState.APPROVED)
        script.approval_actor = user
        script.approval_at = timezone.now()
        script.save(
            update_fields=["gate_state", "approval_actor", "approval_at", "updated_at"]
        )
        record_audit(
            user, AuditAction.UPDATE.value, "script", script.id, "script_approved"
        )
    return script


def request_script_changes(user, script, reason):
    """Gate 2: review -> revision_requested. A reason is required."""
    if script.gate_state != Script.GateState.REVIEW:
        raise DjangoValidationError(
            "script must be in review state to request changes"
        )
    if not reason or not reason.strip():
        raise DjangoValidationError("a rejection reason is required")
    with transaction.atomic():
        script.transition_to(Script.GateState.REVISION_REQUESTED)
        script.rejection_reason = reason.strip()
        script.save(update_fields=["gate_state", "rejection_reason", "updated_at"])
        record_audit(
            user,
            AuditAction.UPDATE.value,
            "script",
            script.id,
            "script_revision_requested",
        )
    return script
