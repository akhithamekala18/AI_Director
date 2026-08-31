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
