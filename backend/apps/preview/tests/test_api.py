# -*- coding: utf-8 -*-
"""Preview API tests (Task 37)."""
import pytest
from rest_framework.test import APIClient
from apps.preview.models import PreviewAsset


@pytest.mark.django_db
class TestPreviewGenerateAPI:
    def test_generate_preview_success(self, auth_client, project, approved_video):
        resp = auth_client.post(
            f"/api/projects/{project.id}/preview/generate/",
            data={"platform_target": "YouTube"}, format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["success"] is True
        p = data["data"]["preview"]
        assert p["status"] == "ready"
        assert p["platform_target"] == "YouTube"
        assert p["approval_state"] == "pending"
        assert p["version"] == 1

    def test_generate_preview_no_gate4(self, auth_client, project):
        resp = auth_client.post(
            f"/api/projects/{project.id}/preview/generate/",
            data={"platform_target": "YouTube"}, format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_generate_preview_no_video(self, auth_client, project, approved_scene_builder):
        resp = auth_client.post(
            f"/api/projects/{project.id}/preview/generate/",
            data={"platform_target": "YouTube"}, format="json",
        )
        assert resp.status_code == 400

    def test_generate_preview_unauthorized(self, project):
        anon = APIClient()
        resp = anon.post(
            f"/api/projects/{project.id}/preview/generate/",
            data={"platform_target": "YouTube"}, format="json",
        )
        assert resp.status_code == 403

    def test_generate_preview_idempotent(self, auth_client, project, approved_video):
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        assert PreviewAsset.objects.filter(project=project).count() == 1
        preview = PreviewAsset.objects.get(project=project)
        assert preview.version == 2
        assert preview.approval_state == PreviewAsset.ApprovalState.PENDING

    def test_generate_preview_resets_approval(self, auth_client, project, approved_video):
        resp = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = resp.json()["data"]["preview"]["id"]
        auth_client.post(f"/api/projects/{project.id}/preview/{pid}/approve/", format="json")
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        preview = PreviewAsset.objects.get(project=project)
        assert preview.approval_state == PreviewAsset.ApprovalState.PENDING


@pytest.mark.django_db
class TestPreviewListAPI:
    def test_list_previews(self, auth_client, project, approved_video):
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        resp = auth_client.get(f"/api/projects/{project.id}/preview/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["previews"]) == 1

    def test_list_previews_empty(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/preview/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["previews"]) == 0


@pytest.mark.django_db
class TestPreviewDetailAPI:
    def test_get_preview_detail(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        resp = auth_client.get(f"/api/projects/{project.id}/preview/{pid}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["preview"]["id"] == pid

    def test_get_preview_not_found(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/preview/99999/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestPreviewApproveRejectAPI:
    def test_approve_preview(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        resp = auth_client.post(f"/api/projects/{project.id}/preview/{pid}/approve/", format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["preview"]["approval_state"] == "approved"
        assert resp.json()["data"]["preview"]["approved_by"] == "preview_user"

    def test_reject_preview(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        resp = auth_client.post(f"/api/projects/{project.id}/preview/{pid}/reject/", data={"reason": "Quality too low"}, format="json")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["preview"]["approval_state"] == "rejected"
        assert resp.json()["data"]["preview"]["rejection_reason"] == "Quality too low"

    def test_reject_preview_requires_reason(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        resp = auth_client.post(f"/api/projects/{project.id}/preview/{pid}/reject/", data={}, format="json")
        assert resp.status_code == 400

    def test_approve_already_approved(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        auth_client.post(f"/api/projects/{project.id}/preview/{pid}/approve/", format="json")
        resp = auth_client.post(f"/api/projects/{project.id}/preview/{pid}/approve/", format="json")
        assert resp.status_code == 400

    def test_cross_team_returns_404(self, outsider_client, auth_client, project, approved_video):
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        resp = outsider_client.get(f"/api/projects/{project.id}/preview/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestPreviewBeforeScheduleInvariant:
    def test_no_approved_blocks_scheduling(self, auth_client, project, approved_video):
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        from apps.preview.services import has_approved_preview
        assert has_approved_preview(auth_client.user, project, "YouTube") is False

    def test_approved_allows_scheduling(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        auth_client.post(f"/api/projects/{project.id}/preview/{pid}/approve/", format="json")
        from apps.preview.services import has_approved_preview
        assert has_approved_preview(auth_client.user, project, "YouTube") is True

    def test_rejected_blocks_scheduling(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        auth_client.post(f"/api/projects/{project.id}/preview/{pid}/reject/", data={"reason": "Not good enough"}, format="json")
        from apps.preview.services import has_approved_preview
        assert has_approved_preview(auth_client.user, project, "YouTube") is False

    def test_regeneration_invalidates_approval(self, auth_client, project, approved_video):
        gen = auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        pid = gen.json()["data"]["preview"]["id"]
        auth_client.post(f"/api/projects/{project.id}/preview/{pid}/approve/", format="json")
        from apps.preview.services import has_approved_preview
        assert has_approved_preview(auth_client.user, project, "YouTube") is True
        auth_client.post(f"/api/projects/{project.id}/preview/generate/", data={"platform_target": "YouTube"}, format="json")
        assert has_approved_preview(auth_client.user, project, "YouTube") is False
