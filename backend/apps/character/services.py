# -*- coding: utf-8 -*-
"""Character Library service layer and Gate 3 orchestration (Phase 2D, Task 23).

Encapsulates the Gate 3 state machine transitions (mirroring the Gate 1/2
patterns from apps.research / apps.script):

  draft -> generating  (G-2: approved Script required)
  generating -> review  [done by the executor]
  review -> approved
  review -> revision_requested  (reason required)
  revision_requested -> generating  (previous version preserved)

Detection depends on the approved Script artifact (G-2: "no character library
before script approval", §22.3.2) via can_generate_characters. Generation runs
through the Phase 2A AsyncJob substrate (job_type character_detection) via
execute_job + the character_detection executor.

Approval also persists the accepted characters to the CharacterLibrary (stable
ids, versioned) so they can be reused across projects while preserving identity
(G-5, §20.1.5). Team isolation is enforced by scoping every query to the user's
memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.audit.services import record_audit
from apps.core.enums import AuditAction
from apps.script.models import Script

from .models import Character, CharacterLibrary, can_generate_characters, current_library_version
from .tasks import enqueue_character_job


def get_character(user, project):
    """Return the project's Character set with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return (
        Character.objects.filter(project=project, team_id__in=team_ids)
        .select_related("project", "script")
        .first()
    )


def _get_approved_script(project):
    """Return the project's approved Script artifact (Gate 2 provenance)."""
    return Script.objects.filter(project=project, gate_state=Script.GateState.APPROVED).first()


def _create_or_get_character(project, script):
    character, created = Character.objects.get_or_create(
        project=project,
        defaults={"team": project.team, "script": script},
    )
    return character


def generate_characters(user, project):
    """Initiate character detection (Gate 3: draft/revision_requested -> generating).

    Enforces the G-2 invariant (approved Script required) and the Gate 3
    starting-state prerequisites, transitions to `generating`, records the
    audit event, and enqueues a Phase 2A AsyncJob (character_detection) to run
    the detection engine.
    """
    script = _get_approved_script(project)
    character = _create_or_get_character(project, script)

    if character.gate_state == Character.GateState.APPROVED:
        raise DjangoValidationError("character set is already approved")
    if character.gate_state == Character.GateState.REVIEW:
        raise DjangoValidationError("character set is already generated and awaiting review")
    if character.gate_state == Character.GateState.GENERATING:
        raise DjangoValidationError("character detection is already in progress")

    regenerating = character.gate_state == Character.GateState.REVISION_REQUESTED

    ok, err = can_generate_characters(character)
    if not ok:
        raise DjangoValidationError(err)

    with transaction.atomic():
        character.transition_to(Character.GateState.GENERATING)
        character.save(update_fields=["gate_state", "updated_at"])
        action = (
            "character_detection_restarted"
            if regenerating
            else "character_detection_started"
        )
        record_audit(user, AuditAction.UPDATE.value, "character", character.id, action)
        enqueue_character_job(user=user, project=project, character_set=character)

    character.refresh_from_db()
    return character


def _library_payload(char):
    """Convert a stored character dict into CharacterLibrary field values."""
    return {
        "name": str(char.get("name") or "").strip(),
        "age": str(char.get("age") or "").strip(),
        "gender": str(char.get("gender") or "").strip(),
        "appearance": char.get("appearance") or {},
        "clothing": char.get("clothing") or {},
        "accessories": char.get("accessories") or [],
        "style": char.get("style") or {},
    }


def _save_characters_to_library(character):
    """Persist accepted characters to the versioned CharacterLibrary (G-5).

    For each character in the set, a new CharacterLibrary row is written under
    its stable ``character_id`` with ``version = previous + 1``. This records
    every version change so identity/reuse is consistent and traceable.
    """
    for char in character.characters or []:
        if not isinstance(char, dict) or not char.get("id"):
            continue
        payload = _library_payload(char)
        version = current_library_version(character.team, char["id"]) + 1
        CharacterLibrary.objects.create(
            team=character.team,
            origin_project=character.project,
            character_id=char["id"],
            version=version,
            **payload,
        )


def approve_character(user, character):
    """Gate 3: review -> approved. Requires a non-empty character set (G-3).

    Only callable from the `review` state. Persists the approval actor/time,
    saves the accepted characters to the CharacterLibrary for reuse, and
    records the audit event.
    """
    if character.gate_state != Character.GateState.REVIEW:
        raise DjangoValidationError(
            "character set must be in review state before it can be approved"
        )
    if not character.characters:
        raise DjangoValidationError(
            "character set cannot be approved without detected characters"
        )
    with transaction.atomic():
        character.transition_to(Character.GateState.APPROVED)
        character.approval_actor = user
        character.approval_at = timezone.now()
        _save_characters_to_library(character)
        character.save(
            update_fields=["gate_state", "approval_actor", "approval_at", "updated_at"]
        )
        record_audit(
            user, AuditAction.UPDATE.value, "character", character.id, "character_set_approved"
        )
    return character


def request_character_changes(user, character, reason):
    """Gate 3: review -> revision_requested. A reason is required."""
    if character.gate_state != Character.GateState.REVIEW:
        raise DjangoValidationError(
            "character set must be in review state to request changes"
        )
    if not reason or not reason.strip():
        raise DjangoValidationError("a rejection reason is required")
    with transaction.atomic():
        character.transition_to(Character.GateState.REVISION_REQUESTED)
        character.rejection_reason = reason.strip()
        character.save(update_fields=["gate_state", "rejection_reason", "updated_at"])
        record_audit(
            user,
            AuditAction.UPDATE.value,
            "character",
            character.id,
            "character_revision_requested",
        )
    return character


def list_library(user, project):
    """Return the team's CharacterLibrary (current version per character id)."""
    team_ids = list(user.memberships.values_list("team_id", flat=True))
    latest_ids = [
        row["character_id"]
        for row in CharacterLibrary.objects.filter(team_id__in=team_ids)
        .values("character_id")
        .annotate(max_version=Max("version"))
    ]
    latest = []
    for cid in latest_ids:
        entry = (
            CharacterLibrary.objects.filter(team_id__in=team_ids, character_id=cid)
            .order_by("-version")
            .first()
        )
        if entry:
            latest.append(entry)
    return latest


def reuse_character(user, project, library_entry):
    """Apply a library character to a project, preserving identity (G-5).

    Appends the library character's attributes (copied verbatim from the
    versioned CharacterLibrary row) to the project's Character set keyed by the
    same stable ``character_id``, so the character renders identically in every
    project (G-5, §20.1.5). Requires membership in the owning team.
    """
    team_ids = user.memberships.values_list("team_id", flat=True)
    if library_entry.team_id not in team_ids:
        raise DjangoValidationError("library character is not in your team")

    character = Character.objects.filter(project=project).first()
    if character is None:
        character = Character.objects.create(
            project=project,
            team=user.memberships.first().team,
            script=_get_approved_script(project),
        )

    entries = character.characters or []
    entries = [
        e for e in entries
        if not (isinstance(e, dict) and e.get("id") == library_entry.character_id)
    ]
    entries.append(
        {
            "id": library_entry.character_id,
            "name": library_entry.name,
            "age": library_entry.age,
            "gender": library_entry.gender,
            "appearance": library_entry.appearance or {},
            "clothing": library_entry.clothing or {},
            "accessories": library_entry.accessories or [],
            "style": library_entry.style or {},
        }
    )
    character.characters = entries
    character.save(update_fields=["characters", "updated_at"])
    record_audit(
        user,
        AuditAction.UPDATE.value,
        "character",
        character.id,
        "character_reused",
    )
    return character
