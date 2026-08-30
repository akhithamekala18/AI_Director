# -*- coding: utf-8 -*-
"""Scene media runtime verification (Phase 2F, Task 25).

Exercises the full end-to-end flow — approved scene package (Gates 2-4) ->
SCENE_MEDIA_GENERATION AsyncJob -> executor -> persisted per-scene media —
using the deterministic offline fake provider. No real external AI provider is
invoked, so REAL PROVIDER RUNTIME: NOT VERIFIED (documented in the report).
"""
import pytest

from apps.ai_orchestration.models import AsyncJob
from apps.scene_media import services

from .helpers import approved_scene_builder, make_project


@pytest.mark.django_db
class TestSceneMediaRuntime:
    def test_concept_to_generated_media_with_fake_provider(self, make_user):
        user = make_user(username="runtime_media")
        project = make_project(user)

        # Gates 1-3 implicit via helpers; Gate 2 script + Gate 3 characters
        # + Gate 4 scene approval produce an approved scene package.
        builder = approved_scene_builder(user, project)
        assert builder.gate_state == "approved"
        assert {s["id"] for s in builder.scenes} == {"s1", "s2"}

        # Task 25: request + run media generation (eager, fake provider).
        job = services.request_scene_media(user, project)
        job.refresh_from_db()
        assert job.job_type == AsyncJob.JobType.SCENE_MEDIA_GENERATION
        assert job.status == AsyncJob.Status.COMPLETED
        assert job.result["count"] == 8

        # Each approved scene produced visual/voice/music/subtitle tied to scene id.
        media = services.list_scene_media(user, project)
        assert media.count() == 8
        for scene_id in ("s1", "s2"):
            for mtype in ("visual", "voice", "music", "subtitle"):
                assert media.filter(scene_id=scene_id, media_type=mtype).exists()
        # Every asset is tied to its stable scene id and keeps stable character ids.
        assert all(m.asset_ref.startswith("mock://") for m in media)
        assert all(m.characters for m in media)
