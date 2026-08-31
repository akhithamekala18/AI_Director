# -*- coding: utf-8 -*-
"""Thumbnail generation service layer (Task 36 / Overview section 20.1.11).

Responsibilities:
  * verify Gate 4 approval server-side (thumbnail requires approved scenes)
  * verify project membership (team isolation)
  * generate thumbnail via the provider abstraction
  * persist the generated ThumbnailAsset
  * audit the generation event

Team isolation: every query is scoped to user.memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from . import engine
from .models import ThumbnailAsset
from .providers.fake import FakeThumbnailProvider


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


_REQUIRES_GATE4_MSG = (
    "thumbnail generation requires an approved scene package (Gate 4)"
)


def list_thumbnails(user, project):
    """List thumbnails for a project with team isolation."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ThumbnailAsset.objects.filter(project=project, team_id__in=team_ids)


def get_thumbnail(user, thumbnail_id):
    """Fetch one thumbnail row with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ThumbnailAsset.objects.filter(id=thumbnail_id, team_id__in=team_ids).first()


def request_thumbnail(user, project, platform_target="", title_text=""):
    """Verify Gate 4, then generate + persist a ThumbnailAsset.

    Returns the created ThumbnailAsset. Raises DjangoValidationError when
    the scene package is not APPROVED or has no scenes.
    """
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")

    builder = get_approved_scene_builder(project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)
    if not builder.scenes:
        raise DjangoValidationError("approved scene package has no scenes")

    provider = FakeThumbnailProvider()
    result = engine.generate_thumbnail(provider, builder.scenes, title_text, platform_target)

    thumb, was_created = ThumbnailAsset.objects.get_or_create(
        project=project,
        platform_target=platform_target,
        defaults={
            "team": project.team,
            "scene_builder": builder,
            "width": 1280,
            "height": 720,
            "status": ThumbnailAsset.Status.READY,
            "asset_ref": result["asset_ref"],
            "provider": result["provider"],
            "provider_metadata": result["provider_metadata"],
            "title_text": title_text,
            "variations": result["variations"],
            "version": 1,
        },
    )

    if not was_created:
        thumb.status = ThumbnailAsset.Status.READY
        thumb.asset_ref = result["asset_ref"]
        thumb.provider = result["provider"]
        thumb.provider_metadata = result["provider_metadata"]
        thumb.title_text = title_text
        thumb.variations = result["variations"]
        thumb.version += 1
        thumb.error_message = ""
        thumb.save()

    record_audit(
        user,
        AuditAction.CREATE.value,
        "thumbnail",
        thumb.id,
        "thumbnail_generated" if was_created else "thumbnail_regenerated",
    )

    return thumb
