# -*- coding: utf-8 -*-
"""Scene Builder service layer and Gate 4 orchestration (Phase 2E, Task 24).

Encapsulates the Gate 4 state machine transitions. Task 24 is synchronous and
deterministic, so it does not enqueue an AsyncJob (the frozen Phase 2A job
substrate has no Task 24 job type and SCENE_MEDIA_GENERATION is reserved for
Task 25). The build step:

  draft / revision_requested -> review   [build now, synchronously]
  review -> approved                     [G-3: Gate 4 approval required]
  review -> revision_requested           [reason required]

Building depends on the four-gate chain: an approved Script (G-2, Gate 2) *and*
an approved Character set (G-3, Gate 3) via can_build_scenes — "no scene library
before both script and characters are approved" (§22.3.2). Characters are
assigned to scenes by stable library ``character_id`` (G-5 identity). Team
isolation is enforced by scoping every query to the user's memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit
from apps.core.enums import AuditAction
from apps.script.models import Script

from . import engine
from .models import SceneBuilder, can_build_scenes


def get_scene_builder(user, project):
    """Return the project's SceneBuilder with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return (
        SceneBuilder.objects.filter(project=project, team_id__in=team_ids)
        .select_related("project", "script", "character_set")
        .first()
    )


def _get_approved_script(project):
    """Return the project's approved Script artifact (Gate 2 provenance)."""
    return Script.objects.filter(
        project=project, gate_state=Script.GateState.APPROVED
    ).first()


def _get_approved_character_set(project):
    """Return the project's approved Character set (Gate 3 provenance)."""
    from apps.character.models import Character

    return Character.objects.filter(
        project=project, gate_state=Character.GateState.APPROVED
    ).first()


def _create_or_get_builder(project, script, character_set):
    builder, _created = SceneBuilder.objects.get_or_create(
        project=project,
        defaults={
            "team": project.team,
            "script": script,
            "character_set": character_set,
        },
    )
    return builder


def build_scenes(user, project):
    """Build the scene package (Gate 4: draft/revision_requested -> review).

    Enforces the Gate 2 + Gate 3 dependency chain (approved Script and approved
    Character set) via can_build_scenes, builds the deterministic scene package
    through the engine, transitions to `review`, and records the audit event.
    """
    script = _get_approved_script(project)
    character_set = _get_approved_character_set(project)
    builder = _create_or_get_builder(project, script, character_set)

    if builder.gate_state == SceneBuilder.GateState.APPROVED:
        raise DjangoValidationError("scene package is already approved")
    if builder.gate_state == SceneBuilder.GateState.REVIEW:
        raise DjangoValidationError("scene package is already built and awaiting review")

    rebuilding = builder.gate_state == SceneBuilder.GateState.REVISION_REQUESTED

    ok, err = can_build_scenes(builder)
    if not ok:
        raise DjangoValidationError(err)

    result = engine.build_scene_package(script, character_set.characters)

    with transaction.atomic():
        builder.scenes = result["scenes"]
        builder.version += 1
        builder.transition_to(SceneBuilder.GateState.REVIEW)
        builder.save(
            update_fields=["scenes", "version", "gate_state", "updated_at"]
        )
        action = (
            "scene_package_rebuilt"
            if rebuilding
            else "scene_package_built"
        )
        record_audit(user, AuditAction.UPDATE.value, "scene", builder.id, action)

    builder.refresh_from_db()
    return builder


def approve_scene_builder(user, builder):
    """Gate 4: review -> approved. Requires a non-empty scene package (G-3)."""
    if builder.gate_state != SceneBuilder.GateState.REVIEW:
        raise DjangoValidationError(
            "scene package must be in review state before it can be approved"
        )
    if not builder.scenes:
        raise DjangoValidationError(
            "scene package cannot be approved without built scenes"
        )
    with transaction.atomic():
        builder.transition_to(SceneBuilder.GateState.APPROVED)
        builder.approval_actor = user
        builder.approval_at = timezone.now()
        builder.save(
            update_fields=["gate_state", "approval_actor", "approval_at", "updated_at"]
        )
        record_audit(
            user, AuditAction.UPDATE.value, "scene", builder.id, "scene_package_approved"
        )
    return builder


def request_scene_changes(user, builder, reason):
    """Gate 4: review -> revision_requested. A reason is required."""
    if builder.gate_state != SceneBuilder.GateState.REVIEW:
        raise DjangoValidationError(
            "scene package must be in review state to request changes"
        )
    if not reason or not reason.strip():
        raise DjangoValidationError("a rejection reason is required")
    with transaction.atomic():
        builder.transition_to(SceneBuilder.GateState.REVISION_REQUESTED)
        builder.rejection_reason = reason.strip()
        builder.save(update_fields=["gate_state", "rejection_reason", "updated_at"])
        record_audit(
            user,
            AuditAction.UPDATE.value,
            "scene",
            builder.id,
            "scene_revision_requested",
        )
    return builder
