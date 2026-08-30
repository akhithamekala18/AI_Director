# -*- coding: utf-8 -*-
"""Regeneration service layer + AsyncJob orchestration (Phase 2G, Task 26).

Responsibilities (matching the documenting contract):

  * verify project membership (anti-existence-leak team isolation),
  * verify Gate 4 approval *server-side* — regeneration is only allowed from an
    APPROVED Scene Builder (never draft/review/revision_requested),
  * enforce G-4 scope: single-scene by default; full only when explicitly
    requested,
  * require that Task 25 media already exists for the target scene(s) so there
    is something to regenerate and to compare against,
  * create + enqueue an AsyncJob(JobType.REGENERATION) using the frozen Phase
    2A job substrate and its executor,
  * in the executor: snapshot the *previous* media versions (SceneMediaVersion)
    so the prior version stays comparable, regenerate ONLY the targeted
    scenes/media (deterministic blast radius), increment versions on the
    affected media rows, and leave every other scene's media untouched,
  * audit important writes,
  * return authoritative persisted state.

Team isolation: every query is scoped to ``user.memberships``; a caller outside
the project's team is treated as not-found (no existence leak).
"""
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.services import create_job
from apps.ai_orchestration.tasks import execute_job
from apps.audit.services import record_audit
from apps.core.enums import AuditAction
from apps.scene_media.models import SceneMedia
from apps.scene_media.providers.fake import FakeSceneMediaProvider

from . import engine
from .models import RegenerationRequest, SceneMediaVersion

_REQUIRES_GATE4_MSG = (
    "regeneration requires an approved scene package (Gate 4)"
)
_REQUIRES_MEDIA_MSG = (
    "no scene media to regenerate; run scene media generation (Task 25) first"
)


def get_approved_scene_builder(project):
    """Return the project's SceneBuilder only if Gate 4 == APPROVED, else None."""
    builder = getattr(project, "scene_builder", None)
    if builder is None:
        return None
    if builder.gate_state != "approved":
        return None
    return builder


def _is_member(user, project):
    return user.memberships.filter(team_id=project.team_id).exists()


def _target_media_for_scene(project, scene_id, media_types):
    """Existing Task 25 media rows for a target scene (or all types)."""
    qs = SceneMedia.objects.filter(project=project, scene_id=scene_id)
    if media_types:
        qs = qs.filter(media_type__in=media_types)
    return qs


def list_regeneration_requests(user, project):
    """List regeneration requests with team isolation."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return RegenerationRequest.objects.filter(
        project=project, team_id__in=team_ids
    )


def get_regeneration_request(user, request_id):
    """Fetch one regeneration request with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return RegenerationRequest.objects.filter(
        id=request_id, team_id__in=team_ids
    ).first()


def _snapshot_media(media, regeneration):
    """Capture an immutable previous-version snapshot of a media row."""
    prior_version = media.version
    SceneMediaVersion.objects.create(
        media=media,
        regeneration=regeneration,
        version=prior_version,
        media_type=media.media_type,
        scene_id=media.scene_id,
        scene_order=media.scene_order,
        asset_ref=media.asset_ref,
        provider=media.provider,
        provider_metadata=media.provider_metadata,
        direction=media.direction,
        narration=media.narration,
        characters=media.characters,
        duration_seconds=media.duration_seconds,
        pacing=media.pacing,
        transition=media.transition,
        voice=media.voice,
        music=media.music,
        caption=media.caption,
    )
    return prior_version


def _apply_regenerated_media(media, payload):
    """Update a media row in place from a regenerated payload (increments version).

    Mirrors the frozen scene_media ``_update_media`` behaviour: the media row is
    overwritten with the new provider result and its version increments, so the
    previous version (snapshotted in SceneMediaVersion) remains comparable.
    """
    media.scene_order = payload["scene_order"]
    media.status = SceneMedia.Status.READY
    media.asset_ref = payload["asset_ref"]
    media.provider = "fake"
    media.provider_metadata = payload["provider_metadata"]
    media.direction = payload.get("visual_direction") or payload.get("narration") or ""
    media.narration = payload["narration"]
    media.characters = payload["characters"]
    media.duration_seconds = payload["duration_seconds"]
    media.pacing = payload["pacing"]
    media.transition = payload["transition"]
    media.voice = payload.get("voice") or {}
    media.music = payload.get("music") or {}
    media.caption = payload.get("caption") or {}
    media.error_message = ""
    media.version += 1
    media.save()
    return media.id


def request_regeneration(user, project, scene_id=None, media_types=None, full=False):
    """Validate prerequisites + G-4 scope, then create + enqueue a REGENERATION job.

    Returns the created AsyncJob. Raises DjangoValidationError on any invalid
    prerequisite, scope, or target.
    """
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")

    builder = get_approved_scene_builder(project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)
    if not builder.scenes:
        raise DjangoValidationError("approved scene package has no scenes")

    # G-4 scope resolution + target validation
    scope, resolved_scene_id = engine.resolve_scope(scene_id, full)
    targets = engine.resolve_targets(builder, scene_id, full, media_types)
    types = targets["media_types"]

    # Ensure there is existing Task 25 media for every target scene involved.
    if scope == "scene":
        media_qs = _target_media_for_scene(project, resolved_scene_id, types)
    else:
        media_qs = SceneMedia.objects.filter(project=project)
        if types:
            media_qs = media_qs.filter(media_type__in=types)
    if not media_qs.exists():
        raise DjangoValidationError(_REQUIRES_MEDIA_MSG)

    regen = RegenerationRequest.objects.create(
        project=project,
        team=project.team,
        scene_builder=builder,
        created_by=user,
        scene_id=resolved_scene_id or "",
        media_types=types,
        full=bool(full),
    )

    job = create_job(
        user,
        project,
        AsyncJob.JobType.REGENERATION,
        metadata={
            "regeneration_request": regen.id,
            "scope": scope,
            "scene_id": resolved_scene_id or None,
            "media_types": types,
            "full": bool(full),
        },
    )
    regen.async_job = job
    regen.save(update_fields=["async_job", "updated_at"])

    record_audit(
        user,
        AuditAction.CREATE.value,
        "regeneration",
        regen.id,
        "regeneration_requested",
    )

    execute_job.delay(job.id)
    job.refresh_from_db()
    regen.refresh_from_db()
    return job


def run_regeneration(job, provider=None):
    """Executor body: snapshot + regenerate the targeted scenes' media only.

    The deterministic blast radius is enforced here: only the targeted scene(s)
    / media types are regenerated; every other scene's media rows are left
    untouched. Each touched media row is snapshotted first (previous version
    comparable) and its version incremented. Returns a structured result dict.
    """
    project = job.project
    req_id = (job.metadata or {}).get("regeneration_request")
    req = RegenerationRequest.objects.filter(pk=req_id).first()
    if req is None:
        raise DjangoValidationError("regeneration request not found")

    if not req.can_transition(RegenerationRequest.Status.RUNNING):
        raise DjangoValidationError(
            f"regeneration request cannot run from {req.status!r}"
        )

    req.transition_to(RegenerationRequest.Status.RUNNING)
    req.save(update_fields=["status", "updated_at"])

    builder = get_approved_scene_builder(project)
    if builder is None:
        req.transition_to(RegenerationRequest.Status.FAILED)
        req.error_message = _REQUIRES_GATE4_MSG
        req.save(update_fields=["status", "error_message", "updated_at"])
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)

    provider = provider or FakeSceneMediaProvider()
    scope = req.full and "full" or "scene"
    scene_id = req.scene_id or None
    targets = engine.resolve_targets(builder, scene_id, scope == "full", req.media_types)
    types = targets["media_types"]

    payloads = engine.build_regeneration_payloads(builder, targets["scopes"], types)

    regenerated_ids = []
    snapshots = 0
    for payload in payloads:
        media_qs = SceneMedia.objects.filter(
            project=project,
            scene_id=payload["scene_id"],
            media_type=payload["media_type"],
        )
        # snapshot previous version for compare, then regenerate in place
        for media in media_qs:
            _snapshot_media(media, req)
            snapshots += 1
            _apply_regenerated_media(media, payload_with_asset(provider, payload))
            regenerated_ids.append(media.id)
            record_audit(
                job.owner,
                AuditAction.UPDATE.value,
                "scene_media",
                media.id,
                "scene_media_regenerated",
            )

    req.media_snapshot_version = snapshots
    req.transition_to(RegenerationRequest.Status.COMPLETED)
    req.save(update_fields=["status", "media_snapshot_version", "updated_at"])

    record_audit(
        job.owner,
        AuditAction.UPDATE.value,
        "regeneration",
        req.id,
        "regeneration_completed",
    )

    return {
        "project": project.id,
        "scene_builder": builder.id,
        "regeneration_request": req.id,
        "scope": scope,
        "scene_id": scene_id,
        "regenerated_ids": regenerated_ids,
        "snapshot_count": snapshots,
        "status": "completed",
    }


def payload_with_asset(provider, payload):
    """Run the provider for one media payload and return a merged record.

    Dispatches the provider call for a single media type (mirroring the frozen
    scene_media engine's per-type dispatch) and merges it into a stable record
    shape (scene_id, scene_order, media_type, asset_ref, provider_metadata,
    voice/music/caption, narration, ...) so persistence code can rely on it.
    """
    mt = payload["media_type"]
    if mt == SceneMedia.MediaType.VISUAL:
        result = provider.generate_visual(payload)
    elif mt == SceneMedia.MediaType.VOICE:
        result = provider.generate_voice(payload)
    elif mt == SceneMedia.MediaType.MUSIC:
        result = provider.generate_music(payload)
    elif mt == SceneMedia.MediaType.SUBTITLE:
        result = provider.generate_subtitle(payload)
    else:
        raise DjangoValidationError(f"unsupported media type: {mt}")

    result["scene_id"] = payload["scene_id"]
    result["scene_order"] = payload["scene_order"]
    result["media_type"] = mt
    result["narration"] = payload["narration"]
    result["characters"] = payload["characters"]
    result["duration_seconds"] = payload["duration_seconds"]
    result["pacing"] = payload["pacing"]
    result["transition"] = payload["transition"]
    result["visual_direction"] = payload.get("visual_direction", "")
    result.setdefault("voice", payload.get("voice") or {})
    result.setdefault("music", payload.get("music") or {})
    result.setdefault("caption", {})
    return result
