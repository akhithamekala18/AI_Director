# -*- coding: utf-8 -*-
"""Celery tasks for async publishing (DG-11).

Uses the existing Celery architecture to publish videos asynchronously.
The task:
1. Validates approval and entry state
2. Loads the social account and decrypts tokens
3. Refreshes token if needed
4. Loads the rendered video file
5. Calls the platform adapter to upload/publish
6. Updates the entry and upload attempt
7. Creates notifications
8. Records audit events
"""
import logging

from celery import shared_task
from django.utils import timezone as dj_tz

logger = logging.getLogger("apps.publishing")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_entry(self, entry_id):
    """Publish a scheduled entry to its target platform.

    Args:
        entry_id: ID of the ScheduledEntry to publish
    """
    from apps.publishing.models import ScheduledEntry, UploadAttempt
    from apps.publishing.services import (
        complete_upload_attempt,
        create_upload_attempt,
        is_approval_valid,
    )
    from apps.publishing.adapters.registry import get_adapter
    from apps.settings_app.services import decrypt_secret
    from apps.core import storage
    from apps.notifications.services import notify_status

    try:
        entry = ScheduledEntry.objects.select_related(
            "social_account", "post", "post__video", "post__project"
        ).get(id=entry_id)
    except ScheduledEntry.DoesNotExist:
        logger.error("ScheduledEntry %s not found", entry_id)
        return {"error": "entry_not_found"}

    # Validate approval
    if not is_approval_valid(entry):
        logger.warning("Entry %s has no valid approval", entry_id)
        return {"error": "approval_invalid"}

    # Validate entry status
    if entry.status != ScheduledEntry.Status.APPROVED:
        logger.warning("Entry %s status is %s, expected approved", entry_id, entry.status)
        return {"error": f"invalid_status:{entry.status}"}

    # Create upload attempt
    try:
        attempt = create_upload_attempt(entry.post.owner, entry)
    except Exception as exc:
        logger.error("Failed to create upload attempt for entry %s: %s", entry_id, exc)
        return {"error": str(exc)}

    try:
        # Get adapter
        adapter = get_adapter(entry.platform)

        # Decrypt access token
        social_account = entry.social_account
        encrypted_tokens = social_account.encrypted_tokens or {}
        access_token_enc = encrypted_tokens.get("access_token", "")
        if not access_token_enc:
            raise ValueError("No access token stored for this account")

        access_token = decrypt_secret(access_token_enc)

        # Try to refresh token if available
        refresh_token_enc = encrypted_tokens.get("refresh_token", "")
        if refresh_token_enc:
            try:
                refresh_token = decrypt_secret(refresh_token_enc)
                new_tokens = adapter.refresh_access_token(refresh_token)
                # Update stored tokens
                social_account.encrypted_tokens = {
                    "access_token": encrypt_secret(new_tokens.access_token),
                    "refresh_token": encrypt_secret(new_tokens.refresh_token) if new_tokens.refresh_token else refresh_token_enc,
                    "token_type": new_tokens.token_type,
                    "expires_in": new_tokens.expires_in,
                    "scope": new_tokens.scope,
                }
                social_account.save()
                access_token = new_tokens.access_token
            except Exception as exc:
                logger.warning("Token refresh failed for account %s: %s", social_account.id, exc)
                # Continue with existing token

        # Load video file
        video = entry.post.video
        if video is None:
            raise ValueError("No video asset associated with this post")

        if video.status != "ready":
            raise ValueError(f"Video asset status is {video.status}, expected ready")

        video_path = storage.get_path(video.asset_ref)
        if not storage.exists(video.asset_ref):
            raise ValueError(f"Video file not found: {video.asset_ref}")

        # Build metadata
        payload = entry.payload_snapshot or {}
        metadata = {
            "title": payload.get("title", entry.post.project.topic),
            "description": payload.get("description", ""),
            "tags": payload.get("tags", []),
            "caption": payload.get("caption", ""),
            "privacy_status": payload.get("privacy_status", "private"),
        }

        # Upload
        media_id = adapter.upload_media(access_token, video_path, metadata)

        # Publish
        result = adapter.publish(access_token, media_id, metadata)

        if result.success:
            complete_upload_attempt(attempt, success=True)
            entry.provider_request_id = result.platform_post_id
            entry.save()
            # Notify
            notify_status(
                entry.post.owner,
                f"Published to {entry.platform}",
                f"Video published successfully to {entry.platform}",
            )
            logger.info("Entry %s published to %s: %s", entry_id, entry.platform, result.platform_post_id)
            return {"entry_id": entry_id, "status": "published", "platform_post_id": result.platform_post_id}
        else:
            failure_kind = UploadAttempt.FailureKind.TRANSIENT if result.retryable else UploadAttempt.FailureKind.PERMANENT
            complete_upload_attempt(attempt, success=False, failure_kind=failure_kind, error=result.error_message)
            logger.warning("Entry %s publish failed: %s", entry_id, result.error_message)
            return {"entry_id": entry_id, "status": "failed", "error": result.error_message}

    except Exception as exc:
        # Determine if retryable
        failure_kind = UploadAttempt.FailureKind.TRANSIENT
        complete_upload_attempt(attempt, success=False, failure_kind=failure_kind, error=str(exc))
        logger.error("Entry %s publish exception: %s", entry_id, exc)

        if attempt.attempt_no < entry.upload_attempts.model.objects.filter(entry=entry).count():
            raise self.retry(exc=exc)

        return {"entry_id": entry_id, "status": "failed", "error": str(exc)}
