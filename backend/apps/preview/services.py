# -*- coding: utf-8 -*-
"""Preview service layer (Task 37 / Overview section 20.2.1).

Responsibilities:
  * verify Gate 4 approval server-side (preview requires approved scenes)
  * verify project membership (team isolation)
  * render platform-accurate preview via the provider abstraction
  * persist the generated PreviewAsset
  * support approval/rejection workflow
  * enforce preview-before-schedule invariant
  * audit the generation and approval events

Team isolation: every query is scoped to user.memberships.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from . import engine
from .models import PreviewAsset
from .providers.fake import FakePreviewProvider


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
    "preview generation requires an approved scene package (Gate 4)"
)


def list_previews(user, project):
    """List previews for a project with team isolation."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return PreviewAsset.objects.filter(project=project, team_id__in=team_ids)


def get_preview(user, preview_id):
    """Fetch one preview row with team isolation, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return PreviewAsset.objects.filter(id=preview_id, team_id__in=team_ids).first()


def get_approved_preview(user, project, platform_target):
    """Return the approved preview for a project+platform, or None."""
    team_ids = user.memberships.values_list("team_id", flat=True)
    return PreviewAsset.objects.filter(
        project=project,
        platform_target=platform_target,
        team_id__in=team_ids,
        approval_state=PreviewAsset.ApprovalState.APPROVED,
        status=PreviewAsset.Status.READY,
    ).first()


def request_preview(user, project, platform_target="YouTube"):
    """Verify Gate 4, then render + persist a PreviewAsset.

    Returns the created/updated PreviewAsset. Raises DjangoValidationError
    when the scene package is not APPROVED or has no scenes.
    """
    if not _is_member(user, project):
        raise DjangoValidationError("not a member of this project's team")

    builder = get_approved_scene_builder(project)
    if builder is None:
        raise DjangoValidationError(_REQUIRES_GATE4_MSG)
    if not builder.scenes:
        raise DjangoValidationError("approved scene package has no scenes")

    # Find the video asset for this platform
    from apps.video.models import VideoAsset

    video = VideoAsset.objects.filter(
        project=project, platform_target=platform_target
    ).first()
    if video is None:
        raise DjangoValidationError(
            f"no video asset found for platform '{platform_target}'"
        )
    if video.status != VideoAsset.Status.READY:
        raise DjangoValidationError(
            f"video asset for '{platform_target}' is not ready"
        )

    provider = FakePreviewProvider()
    result = engine.render_preview(provider, video, platform_target)

    preview, was_created = PreviewAsset.objects.get_or_create(
        project=project,
        platform_target=platform_target,
        defaults={
            "team": project.team,
            "video": video,
            "scene_builder": builder,
            "aspect_ratio": result.get("aspect_ratio", "16:9"),
            "resolution_width": result.get("width", 1920),
            "resolution_height": result.get("height", 1080),
            "status": PreviewAsset.Status.READY,
            "asset_ref": result["asset_ref"],
            "provider": result["provider"],
            "provider_metadata": result["provider_metadata"],
            "duration_seconds": result["duration_seconds"],
            "scene_count": video.scene_count,
            "version": 1,
        },
    )

    if not was_created:
        preview.status = PreviewAsset.Status.READY
        preview.asset_ref = result["asset_ref"]
        preview.provider = result["provider"]
        preview.provider_metadata = result["provider_metadata"]
        preview.duration_seconds = result["duration_seconds"]
        preview.scene_count = video.scene_count
        preview.version += 1
        # Reset approval on re-generation
        preview.approval_state = PreviewAsset.ApprovalState.PENDING
        preview.approved_by = None
        preview.approved_at = None
        preview.rejection_reason = ""
        preview.error_message = ""
        preview.save()

    record_audit(
        user,
        AuditAction.CREATE.value,
        "preview",
        preview.id,
        "preview_generated" if was_created else "preview_regenerated",
    )

    return preview


def approve_preview(user, preview):
    """Approve a preview (reviewer must be a member with appropriate role)."""
    if not _is_member(user, preview.project):
        raise DjangoValidationError("not a member of this project's team")

    if preview.status != PreviewAsset.Status.READY:
        raise DjangoValidationError("preview must be ready before approval")

    if preview.approval_state == PreviewAsset.ApprovalState.APPROVED:
        raise DjangoValidationError("preview is already approved")

    preview.approval_state = PreviewAsset.ApprovalState.APPROVED
    preview.approved_by = user
    preview.approved_at = timezone.now()
    preview.rejection_reason = ""
    preview.save()

    record_audit(
        user,
        AuditAction.UPDATE.value,
        "preview",
        preview.id,
        "preview_approved",
    )

    return preview


def reject_preview(user, preview, reason=""):
    """Reject a preview with a reason."""
    if not _is_member(user, preview.project):
        raise DjangoValidationError("not a member of this project's team")

    if preview.status != PreviewAsset.Status.READY:
        raise DjangoValidationError("preview must be ready before rejection")

    if not reason or not reason.strip():
        raise DjangoValidationError("rejection reason is required")

    preview.approval_state = PreviewAsset.ApprovalState.REJECTED
    preview.rejection_reason = reason.strip()
    preview.save()

    record_audit(
        user,
        AuditAction.UPDATE.value,
        "preview",
        preview.id,
        "preview_rejected",
    )

    return preview


def has_approved_preview(user, project, platform_target):
    """Check if an approved preview exists for scheduling (invariant check)."""
    return get_approved_preview(user, project, platform_target) is not None
