# -*- coding: utf-8 -*-
"""AsyncJob executor integration tests for REGENERATION."""
import pytest

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.tasks import JOB_EXECUTORS, execute_job
from apps.regeneration import tasks
from apps.regeneration.models import RegenerationRequest, SceneMediaVersion

from .helpers import make_project, setup_media


@pytest.mark.django_db
class TestExecutorRegistration:
    def test_regeneration_executor_registered(self):
        handler = JOB_EXECUTORS.get(AsyncJob.JobType.REGENERATION)
        assert handler is not None

    def test_handler_is_run_regeneration_executor(self):
        handler = JOB_EXECUTORS.get(AsyncJob.JobType.REGENERATION)
        assert handler is tasks.run_regeneration_executor


@pytest.mark.django_db
class TestExecutorSuccess:
    def test_job_runs_and_persists_result(self, make_user):
        user = make_user(username="exec_ok")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user,
            scene_builder=builder, scene_id="s1", media_types=["voice"],
        )
        job = AsyncJob.objects.create(
            team=project.team, project=project, owner=user,
            job_type=AsyncJob.JobType.REGENERATION,
            metadata={"regeneration_request": req.id, "scene_id": "s1", "media_types": ["voice"]},
        )
        req.async_job = job
        req.save(update_fields=["async_job"])
        result = execute_job.delay(job.id).get()
        job.refresh_from_db()
        req.refresh_from_db()
        assert result["completed"] is True
        assert job.status == AsyncJob.Status.COMPLETED
        assert job.started_at is not None and job.completed_at is not None
        assert job.result["regeneration_request"] == req.id
        assert job.result["status"] == "completed"
        assert req.status == RegenerationRequest.Status.COMPLETED

    def test_snapshots_created_during_execution(self, make_user):
        user = make_user(username="exec_snap")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user,
            scene_builder=builder, scene_id="s1", media_types=["voice"],
        )
        job = AsyncJob.objects.create(
            team=project.team, project=project, owner=user,
            job_type=AsyncJob.JobType.REGENERATION,
            metadata={"regeneration_request": req.id, "scene_id": "s1", "media_types": ["voice"]},
        )
        req.async_job = job
        req.save(update_fields=["async_job"])
        execute_job.delay(job.id).get()
        snaps = SceneMediaVersion.objects.filter(regeneration=req)
        assert snaps.count() >= 1

    def test_other_scenes_untouched(self, make_user):
        user = make_user(username="exec_blast")
        project = make_project(user)
        setup_media(user, project)
        from apps.scene_media.models import SceneMedia
        s2_before = list(
            SceneMedia.objects.filter(project=project, scene_id="s2").values_list("version", flat=True)
        )
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user,
            scene_builder=builder, scene_id="s1", media_types=["voice"],
        )
        job = AsyncJob.objects.create(
            team=project.team, project=project, owner=user,
            job_type=AsyncJob.JobType.REGENERATION,
            metadata={"regeneration_request": req.id, "scene_id": "s1", "media_types": ["voice"]},
        )
        req.async_job = job
        req.save(update_fields=["async_job"])
        execute_job.delay(job.id).get()
        s2_after = list(
            SceneMedia.objects.filter(project=project, scene_id="s2").values_list("version", flat=True)
        )
        assert s2_before == s2_after


@pytest.mark.django_db
class TestExecutorFailure:
    def test_missing_request_marks_job_failed(self, make_user):
        user = make_user(username="exec_fail")
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
