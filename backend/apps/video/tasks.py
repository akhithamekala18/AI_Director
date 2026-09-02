# -*- coding: utf-8 -*-
"""Celery task for async video rendering (DG-9)."""
import logging

from celery import shared_task

logger = logging.getLogger("apps.video")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def render_video(self, video_id, platform_target="YouTube"):
    """Render a video asynchronously using MoviePy + FFmpeg."""
    from apps.video.models import VideoAsset
    from apps.video.providers.moviepy_provider import MoviePyVideoProvider

    try:
        video = VideoAsset.objects.get(id=video_id)
    except VideoAsset.DoesNotExist:
        logger.error("VideoAsset %s not found", video_id)
        return {"error": "video_not_found"}

    video.status = VideoAsset.Status.GENERATING
    video.error_message = ""
    video.save(update_fields=["status", "error_message", "updated_at"])

    try:
        builder = video.scene_builder
        if builder is None or builder.gate_state != "approved":
            raise ValueError("Scene builder not approved")

        scenes = builder.scenes or []
        if not scenes:
            raise ValueError("No scenes to render")

        provider = MoviePyVideoProvider()
        result = provider.composite(scenes, platform_target)

        video.status = VideoAsset.Status.READY
        video.asset_ref = result["asset_ref"]
        video.provider = result["provider"]
        video.provider_metadata = result["provider_metadata"]
        video.duration_seconds = result["duration_seconds"]
        video.error_message = ""
        video.save()

        logger.info("Video %s rendered successfully", video_id)
        return {"video_id": video_id, "status": "ready", "asset_ref": result["asset_ref"]}

    except Exception as exc:
        video.retry_count += 1
        video.error_message = str(exc)
        if video.retry_count >= video.max_retries:
            video.status = VideoAsset.Status.FAILED
        else:
            video.status = VideoAsset.Status.PENDING
        video.save(update_fields=["status", "error_message", "retry_count", "updated_at"])

        logger.error("Video %s render failed (attempt %d/%d): %s", video_id, video.retry_count, video.max_retries, exc)

        if video.retry_count < video.max_retries:
            raise self.retry(exc=exc)

        return {"video_id": video_id, "status": "failed", "error": str(exc)}
