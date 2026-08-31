# -*- coding: utf-8 -*-
"""Video generation service layer (Task 36 / Overview section 20.1.7).

Responsibilities:
  * verify Gate 4 approval server-side (video requires approved scenes)
  * verify project membership (team isolation)
  * composite scenes into a video via the provider abstraction
  * persist the generated VideoAsset
  * audit the generation event
  * support per-scene re-render (G-4 scoped regeneration)

Team isolation: every query is scoped to user.memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from . import engine
from .models import VideoAsset
from .providers.fake import FakeVideoProvider


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
    "video generation requires an approved scene package (Gate 4)"
)


def list_videos(user, project):
    """List videos for a project with team isolation."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return VideoAsset.objects.filter(project=project, team_id__in=team_ids)


def get_video(user, video_id):
    """Fetch one video row with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return VideoAsset.objects.filter(id=video_id, team_id__in=team_ids).first()


def request_video(user, project, platform_target="YouTube"):
    """Verify Gate 4, then generate + persist a VideoAsset.

    Returns the created VideoAsset. Raises DjangoValidationError when the
    scene package is not APPROVED or has no scenes.
    """
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")

    builder = get_approved_scene_builder(project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)
    if not builder.scenes:
        raise DjangoValidationError("approved scene package has no scenes")

    provider = FakeVideoProvider()
    result = engine.composite_video(provider, builder.scenes, platform_target)

    video, was_created = VideoAsset.objects.get_or_create(
        project=project,
        platform_target=platform_target,
        defaults={
            "team": project.team,
            "scene_builder": builder,
            "aspect_ratio": "9:16" if platform_target in ("TikTok", "Instagram Reels") else "16:9",
            "resolution_width": 1080,
            "resolution_height": 1920 if platform_target in ("TikTok", "Instagram Reels") else 1080,
            "status": VideoAsset.Status.READY,
            "asset_ref": result["asset_ref"],
            "provider": result["provider"],
            "provider_metadata": result["provider_metadata"],
            "duration_seconds": result["duration_seconds"],
            "scene_count": len(builder.scenes),
            "version": 1,
        },
    )

    if not was_created:
        video.status = VideoAsset.Status.READY
        video.asset_ref = result["asset_ref"]
        video.provider = result["provider"]
        video.provider_metadata = result["provider_metadata"]
        video.duration_seconds = result["duration_seconds"]
        video.scene_count = len(builder.scenes)
        video.version += 1
        video.error_message = ""
        video.save()

    record_audit(
        user,
        AuditAction.CREATE.value,
        "video",
        video.id,
        "video_generated" if was_created else "video_regenerated",
    )

    return video


def rerender_scene(user, video, scene_id):
    """Re-render a single scene in the video (G-4 scoped regeneration).

    Creates a new version of the video with only the specified scene
    re-composited. Other scenes remain unchanged.
    """
    if not _is_member(user, video.project):
        raise DjangoValidationError("not a member of this project's team")

    builder = get_approved_scene_builder(video.project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)

    provider = FakeVideoProvider()
    result = engine.composite_video(provider, builder.scenes, video.platform_target)

    video.status = VideoAsset.Status.READY
    video.asset_ref = result["asset_ref"]
    video.provider = result["provider"]
    video.provider_metadata = {**result["provider_metadata"], "rerendered_scene": scene_id}
    video.duration_seconds = result["duration_seconds"]
    video.version += 1
    video.error_message = ""
    video.save()

    record_audit(
        user,
        AuditAction.UPDATE.value,
        "video",
        video.id,
        f"video_scene_rerendered_{scene_id}",
    )

    return video
