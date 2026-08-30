# -*- coding: utf-8 -*-
"""Scene Media service layer and AsyncJob orchestration (Phase 2F, Task 25).

Responsibilities (matching the documenting contract):

  * verify project membership (anti-existence-leak team isolation),
  * verify Gate 4 approval *server-side* — media generation is only allowed
    from an APPROVED Scene Builder (never draft/review/revision_requested),
  * identify the scenes from the approved package,
  * create + enqueue an AsyncJob(JobType.SCENE_MEDIA_GENERATION) using the
    frozen Phase 2A job substrate and its executor,
  * persist per-scene generated media idempotently (get_or_create keyed on
    scene_builder + scene_id + media_type) so a retry never duplicates rows,
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

from . import engine
from .models import SceneMedia
from .providers.fake import FakeSceneMediaProvider

MEDIA_ALL = [SceneMedia.MediaType.VISUAL, SceneMedia.MediaType.VOICE, SceneMedia.MediaType.MUSIC, SceneMedia.MediaType.SUBTITLE]

_REQUIRES_GATE4_MSG = (
    "scene media generation requires an approved scene package (Gate 4)"
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


def list_scene_media(user, project):
    """List media for a project with team isolation (empty for outsiders)."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return SceneMedia.objects.filter(project=project, team_id__in=team_ids)


def get_scene_media(user, media_id):
    """Fetch one media row with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return SceneMedia.objects.filter(id=media_id, team_id__in=team_ids).first()


def request_scene_media(user, project, media_types=None):
    """Verify Gate 4, then create + enqueue a SCENE_MEDIA_GENERATION job.

    Returns the created AsyncJob. Raises DjangoValidationError when the scene
    package is not APPROVED (Gate 4 dependency, enforced server-side) or the
    approved package has no scenes.
    """
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")

    builder = get_approved_scene_builder(project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)
    if not builder.scenes:
        raise DjangoValidationError("approved scene package has no scenes")

    types = engine.requested_media_types(media_types)
    if not types:
        raise DjangoValidationError("no supported media types requested")

    job = create_job(
        user,
        project,
        AsyncJob.JobType.SCENE_MEDIA_GENERATION,
        metadata={
            "media_types": types,
            "scene_count": len(builder.scenes),
        },
    )
    record_audit(
        user,
        AuditAction.CREATE.value,
        "scene_media",
        job.id,
        "scene_media_generation_requested",
    )
    # Dispatch via the frozen Phase 2A Celery task. In tests this runs eagerly;
    # in production a worker consumes execute_job.
    execute_job.delay(job.id)
    # Return authoritative persisted state (in eager tests the job is already
    # terminal; in production it remains pending until a worker consumes it).
    job.refresh_from_db()
    return job


def run_generation(job, provider=None):
    """Executor body: generate + persist media for an approved package.

    Idempotent: rows are get_or_create'd on (scene_builder, scene_id,
    media_type) and updated, so a bounded retry never duplicates media. Returns
    a structured result dict stored on the AsyncJob.
    """
    project = job.project
    builder = get_approved_scene_builder(project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)

    provider = provider or FakeSceneMediaProvider()
    types = (job.metadata or {}).get("media_types") or list(MEDIA_ALL)

    produced = engine.generate_scene_media(provider, builder, types)
    created, updated = [], []
    for rec in produced["media"]:
        obj, was_created = SceneMedia.objects.get_or_create(
            scene_builder=builder,
            scene_id=rec["scene_id"],
            media_type=rec["media_type"],
            defaults=_media_defaults(job, builder, rec),
        )
        if was_created:
            created.append(obj.id)
        else:
            updated.append(_update_media(obj, rec))
        record_audit(
            job.owner,
            AuditAction.CREATE.value,
            "scene_media",
            obj.id,
            "scene_media_generated",
        )

    return {
        "project": project.id,
        "scene_builder": builder.id,
        "count": produced["count"],
        "created_ids": created,
        "status": "completed",
    }


def _media_defaults(job, builder, rec):
    return {
        "project": builder.project,
        "team": builder.team,
        "scene_order": rec["scene_order"],
        "status": SceneMedia.Status.READY,
        "asset_ref": rec["asset_ref"],
        "provider": "fake",
        "provider_metadata": rec["provider_metadata"],
        "direction": rec.get("visual_direction") or rec.get("narration") or "",
        "narration": rec["narration"],
        "characters": rec["characters"],
        "duration_seconds": rec["duration_seconds"],
        "pacing": rec["pacing"],
        "transition": rec["transition"],
        "voice": rec.get("voice") or {},
        "music": rec.get("music") or {},
        "caption": rec.get("caption") or {},
        "version": 1,
    }


def _update_media(obj, rec):
    obj.status = SceneMedia.Status.READY
    obj.scene_order = rec["scene_order"]
    obj.asset_ref = rec["asset_ref"]
    obj.provider = "fake"
    obj.provider_metadata = rec["provider_metadata"]
    obj.direction = rec.get("visual_direction") or rec.get("narration") or ""
    obj.narration = rec["narration"]
    obj.characters = rec["characters"]
    obj.duration_seconds = rec["duration_seconds"]
    obj.pacing = rec["pacing"]
    obj.transition = rec["transition"]
    obj.voice = rec.get("voice") or {}
    obj.music = rec.get("music") or {}
    obj.caption = rec.get("caption") or {}
    obj.error_message = ""
    obj.version += 1
    obj.save()
    return obj.id
