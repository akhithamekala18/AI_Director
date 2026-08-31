# -*- coding: utf-8 -*-
import pytest
from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db
class TestSocialAccountAPI:
    def test_connect_social_account(self, auth_client):
        resp = auth_client.post("/api/publishing/social-accounts/connect/",
            data={"platform": "YouTube", "platform_account_id": "yt_999", "display_name": "My YT"},
            format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["success"] is True
        assert resp.json()["data"]["account"]["platform"] == "YouTube"

    def test_list_social_accounts(self, auth_client, social_account):
        resp = auth_client.get("/api/publishing/social-accounts/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["accounts"]) == 1

    def test_disconnect_social_account(self, auth_client, social_account):
        resp = auth_client.post(f"/api/publishing/social-accounts/{social_account.id}/disconnect/")
        assert resp.status_code == 200
        assert resp.json()["data"]["account"]["status"] == "revoked"

    def test_cross_team_cannot_list(self, outsider_client, social_account):
        resp = outsider_client.get("/api/publishing/social-accounts/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["accounts"]) == 0

@pytest.mark.django_db
class TestPostAPI:
    def test_create_post(self, auth_client, project):
        resp = auth_client.post(f"/api/projects/{project.id}/publishing/posts/create/",
            data={}, format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["post"]["status"] == "draft"

    def test_list_posts(self, auth_client, project, post):
        resp = auth_client.get(f"/api/projects/{project.id}/publishing/posts/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["posts"]) == 1

    def test_get_post_detail(self, auth_client, project, post):
        resp = auth_client.get(f"/api/projects/{project.id}/publishing/posts/{post.id}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["post"]["id"] == post.id

    def test_cross_team_cannot_see_posts(self, outsider_client, project, post):
        resp = outsider_client.get(f"/api/projects/{project.id}/publishing/posts/")
        assert resp.status_code in (403, 404)

@pytest.mark.django_db
class TestEntryAPI:
    def test_create_entry(self, auth_client, post, social_account):
        future = (timezone.now() + timedelta(hours=24)).isoformat()
        resp = auth_client.post(f"/api/projects/{post.project_id}/publishing/entries/create/",
            data={"post_id": post.id, "social_account_id": social_account.id, "scheduled_utc": future},
            format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["entry"]["platform"] == "YouTube"

    def test_list_entries(self, auth_client, post, scheduled_entry):
        resp = auth_client.get(f"/api/projects/{post.project_id}/publishing/entries/?post_id={post.id}")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["entries"]) == 1

    def test_cancel_entry(self, auth_client, scheduled_entry):
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/cancel/",
            format="json")
        assert resp.status_code == 200
        assert resp.json()["data"]["entry"]["status"] == "canceled"

@pytest.mark.django_db
class TestApprovalAPI:
    def test_approve_entry(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={"reason": "Looks good"}, format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["approval"]["decision"] == "approve"
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "approved"

    def test_reject_entry(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reject/",
            data={"reason": "Needs changes"}, format="json")
        assert resp.status_code == 200
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "rejected"

    def test_cannot_approve_scheduled(self, auth_client, scheduled_entry):
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        assert resp.status_code == 400

    def test_list_approvals(self, auth_client, scheduled_entry):
        from apps.publishing.models import Approval
        Approval.objects.create(entry=scheduled_entry, actor=auth_client.user,
            decision="approve", expires_at=timezone.now() + timedelta(hours=12))
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.get(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approvals/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["approvals"]) == 1

@pytest.mark.django_db
class TestUploadEnforcement:
    def test_upload_requires_approved(self, auth_client, scheduled_entry):
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code == 400

    def test_upload_requires_valid_approval(self, auth_client, scheduled_entry):
        scheduled_entry.status = "approved"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code == 400

    def test_upload_succeeds_with_valid_approval(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code == 200, resp.content
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "uploading"

    def test_upload_blocks_without_approval(self, auth_client, scheduled_entry):
        scheduled_entry.status = "approved"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code == 400

@pytest.mark.django_db
class TestTeamIsolation:
    def test_outsider_cannot_create_post(self, outsider_client, project):
        resp = outsider_client.post(f"/api/projects/{project.id}/publishing/posts/create/",
            data={}, format="json")
        assert resp.status_code in (403, 404)

    def test_outsider_cannot_approve(self, outsider_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = outsider_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        assert resp.status_code in (403, 404)

    def test_outsider_cannot_upload(
self, outsider_client, scheduled_entry):
        proj_id = scheduled_entry.post.project_id
        resp = outsider_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code in (403, 404)

@pytest.mark.django_db
class TestPendingApprovals:
    def test_pending_approvals_list(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        resp = auth_client.get("/api/publishing/pending-approvals/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["pending"]) == 1

@pytest.mark.django_db
class TestPublishingHistory:
    def test_history(self, auth_client, project, scheduled_entry):
        resp = auth_client.get(f"/api/projects/{project.id}/publishing/history/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["history"]) == 1


@pytest.mark.django_db
class TestRescheduleApprovalInvalidation:
    def test_reschedule_invalidates_approvals(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "approved"
        new_utc = (timezone.now() + timedelta(hours=72)).isoformat()
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reschedule/",
            data={"scheduled_utc": new_utc}, format="json")
        assert resp.status_code == 200, resp.content
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "ready_for_approval"
        assert resp.json()["data"]["invalidated_approvals"] >= 1

    def test_reschedule_cannot_reschedule_canceled(self, auth_client, scheduled_entry):
        scheduled_entry.status = "canceled"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        new_utc = (timezone.now() + timedelta(hours=72)).isoformat()
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reschedule/",
            data={"scheduled_utc": new_utc}, format="json")
        assert resp.status_code == 400

    def test_reschedule_requires_valid_status(self, auth_client, scheduled_entry):
        scheduled_entry.status = "uploading"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        new_utc = (timezone.now() + timedelta(hours=72)).isoformat()
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reschedule/",
            data={"scheduled_utc": new_utc}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestChangePlatformApprovalInvalidation:
    def test_change_platform_invalidates_approvals(self, auth_client, scheduled_entry, social_account):
        from apps.publishing.models import SocialAccount
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "approved"
        sa2 = SocialAccount.objects.create(
            owner=auth_client.user, team=social_account.team,
            platform="TikTok", platform_account_id="tt_999",
        )
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/change-platform/",
            data={"platform": "TikTok", "social_account_id": sa2.id}, format="json")
        assert resp.status_code == 200, resp.content
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "ready_for_approval"
        assert scheduled_entry.platform == "TikTok"
        assert resp.json()["data"]["invalidated_approvals"] >= 1


@pytest.mark.django_db
class TestApprovalExpiry:
    def test_expired_approval_blocks_upload(self, auth_client, scheduled_entry):
        from apps.publishing.models import Approval
        scheduled_entry.status = "approved"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        Approval.objects.create(
            entry=scheduled_entry, actor=auth_client.user,
            decision="approve",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code == 400

    def test_valid_approval_allows_upload(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/",
            format="json")
        assert resp.status_code == 200

    def test_recheck_expired_approvals(self, auth_client, scheduled_entry):
        from apps.publishing.models import Approval
        scheduled_entry.status = "approved"
        scheduled_entry.save()
        Approval.objects.create(
            entry=scheduled_entry, actor=auth_client.user,
            decision="approve",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = auth_client.post("/api/publishing/recheck-approvals/", format="json")
        assert resp.status_code == 200
        assert resp.json()["data"]["expired_count"] >= 1
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "ready_for_approval"


@pytest.mark.django_db
class TestRejectionLandsInDraft:
    def test_rejection_sets_draft(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reject/",
            data={"reason": "Not ready"}, format="json")
        assert resp.status_code == 200
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "rejected"

    def test_can_reschedule_after_rejection(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reject/",
            data={"reason": "Fix needed"}, format="json")
        new_utc = (timezone.now() + timedelta(hours=72)).isoformat()
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/reschedule/",
            data={"scheduled_utc": new_utc}, format="json")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestPayloadSnapshotOnApproval:
    def test_approve_stores_payload(self, auth_client, scheduled_entry):
        from apps.publishing.services import approve_entry_with_payload
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        payload = {"title": "Test Video", "description": "A test"}
        approve_entry_with_payload(auth_client.user, scheduled_entry, payload=payload)
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.payload_snapshot == payload

    def test_approve_without_payload(self, auth_client, scheduled_entry):
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/",
            data={}, format="json")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestRetrySchedule1515:
    def test_wait_seconds(self):
        from apps.publishing import services
        assert services._get_retry_wait_seconds(1) == 0
        assert services._get_retry_wait_seconds(2) == 60
        assert services._get_retry_wait_seconds(3) == 300
        assert services._get_retry_wait_seconds(4) == 900


@pytest.mark.django_db
class TestTransientRetrySchedule:
    def test_transient_failure_sets_retry(self, auth_client, scheduled_entry):
        from apps.publishing.models import UploadAttempt
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        scheduled_entry.refresh_from_db()
        attempt = scheduled_entry.upload_attempts.first()
        services.complete_upload_attempt(attempt, False, UploadAttempt.FailureKind.TRANSIENT, "timeout")
        attempt.refresh_from_db()
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "upload_failed"
        assert attempt.next_retry_at is not None
        assert attempt.failure_kind == "transient"


@pytest.mark.django_db
class TestPermanentFailure:
    def test_permanent_failure_no_retry(self, auth_client, scheduled_entry):
        from apps.publishing.models import UploadAttempt
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        scheduled_entry.refresh_from_db()
        attempt = scheduled_entry.upload_attempts.first()
        services.complete_upload_attempt(attempt, False, UploadAttempt.FailureKind.PERMANENT, "expired auth")
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "failed_pending_user"
        retryable, reason = services.can_retry_entry(scheduled_entry)
        assert not retryable
        # Entry is in failed_pending_user, not upload_failed, so can_retry rejects by status
        assert "failed_pending_user" in reason


@pytest.mark.django_db
class TestIdempotentPublish:
    def test_second_upload_rejected_after_success(self, auth_client, scheduled_entry):
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        scheduled_entry.refresh_from_db()
        attempt = scheduled_entry.upload_attempts.first()
        services.complete_upload_attempt(attempt, True)
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "published"
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestMaxAttemptsExceeded:
    def test_exhausted_retries_to_failed(self, auth_client, scheduled_entry):
        from apps.publishing.models import UploadAttempt
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        for i in range(4):
            attempt = UploadAttempt.objects.create(entry=scheduled_entry, attempt_no=i+1, status=UploadAttempt.Status.FAILED, failure_kind=UploadAttempt.FailureKind.TRANSIENT)
        services.complete_upload_attempt(attempt, False, UploadAttempt.FailureKind.TRANSIENT, "timeout")
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "failed"
        retryable, reason = services.can_retry_entry(scheduled_entry)
        assert not retryable
        # Entry is in failed, not upload_failed, so can_retry rejects by status
        assert "failed" in reason


@pytest.mark.django_db
class TestRetryTrigger:
    def test_trigger_retry(self, auth_client, scheduled_entry):
        from apps.publishing.models import UploadAttempt
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        scheduled_entry.refresh_from_db()
        attempt = scheduled_entry.upload_attempts.first()
        services.complete_upload_attempt(attempt, False, UploadAttempt.FailureKind.TRANSIENT, "timeout")
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "upload_failed"
        resp = auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/retry/", data={}, format="json")
        assert resp.status_code == 200
        scheduled_entry.refresh_from_db()
        assert scheduled_entry.status == "uploading"
        assert scheduled_entry.upload_attempts.count() == 2

    def test_retry_status(self, auth_client, scheduled_entry):
        from apps.publishing.models import UploadAttempt
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        scheduled_entry.refresh_from_db()
        attempt = scheduled_entry.upload_attempts.first()
        services.complete_upload_attempt(attempt, False, UploadAttempt.FailureKind.TRANSIENT, "timeout")
        scheduled_entry.refresh_from_db()
        resp = auth_client.get(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/retry-status/")
        assert resp.status_code == 200
        data = resp.json()["data"]["retry_status"]
        assert data["total_attempts"] == 1
        assert data["retryable"] is True


@pytest.mark.django_db
class TestApprovalRevalidationOnRetry:
    def test_retry_blocked_without_approval(self, auth_client, scheduled_entry):
        from apps.publishing.models import UploadAttempt, Approval
        from apps.publishing import services
        scheduled_entry.status = "ready_for_approval"
        scheduled_entry.save()
        proj_id = scheduled_entry.post.project_id
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/approve/", data={}, format="json")
        auth_client.post(f"/api/projects/{proj_id}/publishing/entries/{scheduled_entry.id}/upload/", data={}, format="json")
        scheduled_entry.refresh_from_db()
        attempt = scheduled_entry.upload_attempts.first()
        services.complete_upload_attempt(attempt, False, UploadAttempt.FailureKind.TRANSIENT, "timeout")
        scheduled_entry.refresh_from_db()
        Approval.objects.filter(entry=scheduled_entry).update(invalidated=True, invalidated_at=timezone.now())
        retryable, reason = services.can_retry_entry(scheduled_entry)
        assert not retryable
        assert "approval" in reason.lower()
