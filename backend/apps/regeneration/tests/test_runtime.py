# -*- coding: utf-8 -*-
"""Runtime verification test for regeneration."""
import json

import pytest
from rest_framework.test import APIClient

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.tasks import execute_job
from apps.regeneration.models import RegenerationRequest, SceneMediaVersion
from apps.scene_media.models import SceneMedia

from .helpers import make_project, setup_media

REGEN_CREATE = "/api/projects/{}/regeneration/regenerate/"
REGEN_LIST = "/api/projects/{}/regeneration/"


@pytest.mark.django_db
class TestRuntimeVerification:
    def test_full_pipeline_end_to_end(self, make_user, api_client):
        client = api_client(username="runtime_user")
        user = client.user
        project = make_project(user)
        setup_media(user, project)
        original_s1_voice = SceneMedia.objects.get(project=project, scene_id="s1", media_type="voice")
        original_s1_asset = original_s1_voice.asset_ref
        original_s1_narration = original_s1_voice.narration
        resp = client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        assert resp.status_code == 202
        job_data = resp.json()["data"]["job"]
        assert job_data["job_type"] == "regeneration"
        job = AsyncJob.objects.get(id=job_data["id"])
        assert job.job_type == AsyncJob.JobType.REGENERATION
        assert job.status == AsyncJob.Status.COMPLETED
        assert job.result["status"] == "completed"
        req = RegenerationRequest.objects.filter(async_job=job).first()
        assert req is not None
        assert req.status == RegenerationRequest.Status.COMPLETED
        assert req.scene_id == "s1"
        snaps = SceneMediaVersion.objects.filter(regeneration=req)
        assert snaps.count() >= 1
        snap = snaps.first()
        assert snap.asset_ref == original_s1_asset
        assert snap.narration == original_s1_narration
        original_s1_voice.refresh_from_db()
        assert original_s1_voice.version > 1
        s2_media = list(SceneMedia.objects.filter(project=project, scene_id="s2"))
        for m in s2_media:
            assert m.version == 1
        outsider_client = api_client(username="runtime_outsider")
        assert outsider_client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        ).status_code == 404
        assert outsider_client.get(REGEN_LIST.format(project.id)).status_code == 404
        anon = APIClient()
        assert anon.post(
            REGEN_CREATE.format(project.id), {}, format="json"
        ).status_code == 403
        job_str = json.dumps(job.result)
        for secret in ["sk-", "bearer", "api_key", "password", "secret"]:
            assert secret.lower() not in job_str.lower()

    def test_failed_job_produces_deterministic_failure(self, make_user):
        user = make_user(username="runtime_fail")
        project = make_project(user)
        job = AsyncJob.objects.create(
            team=project.team, project=project, owner=user,
            job_type=AsyncJob.JobType.REGENERATION,
            metadata={"regeneration_request": 999999},
        )
        execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        assert "not found" in job.error_message.lower()

    def test_list_endpoint_returns_snapshots(self, api_client):
        client = api_client(username="runtime_snaps")
        user = client.user
        project = make_project(user)
        setup_media(user, project)
        client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        resp = client.get(REGEN_LIST.format(project.id))
        data = resp.json()["data"]["regeneration"]
        assert len(data) >= 1
        assert "snapshots" in data[0]
        assert len(data[0]["snapshots"]) >= 1
