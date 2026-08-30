# -*- coding: utf-8 -*-
"""AsyncJob executor integration tests (frozen Phase 2A SCENE_MEDIA_GENERATION).

Drives the job through the Phase 2A Celery task (eager mode) and verifies the
registered scene media executor, success/failure, ordered/bounded retries, and
idempotent persistence.
"""
import pytest

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.services import retry_job
from apps.ai_orchestration.tasks import JOB_EXECUTORS, execute_job
from apps.scene_media import services, tasks
from apps.scene_media.models import SceneMedia
from apps.scene_media.providers.base import SceneMediaProviderError
from apps.scene_media.providers.fake import FakeSceneMediaProvider

from .helpers import approved_scene_builder, make_project


class _FailingProvider(FakeSceneMediaProvider):
    def generate_visual(self, payload):
        raise SceneMediaProviderError("media provider down", retryable=True)


@pytest.mark.django_db
class TestExecutorRegistration:
    def test_executor_registered_with_frozen_substrate(self):
        handler = JOB_EXECUTORS.get(AsyncJob.JobType.SCENE_MEDIA_GENERATION)
        assert handler is not None
        assert handler is tasks.run_scene_media_generation


@pytest.mark.django_db
class TestExecutorSuccess:
    def test_job_runs_and_persists_media(self, make_user):
        user = make_user(username="exec_ok")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.SCENE_MEDIA_GENERATION,
            metadata={"media_types": ["voice", "music"]},
        )
        result = execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert result["completed"] is True
        assert job.status == AsyncJob.Status.COMPLETED
        assert job.started_at is not None and job.completed_at is not None
        assert job.result["count"] == 4
        assert job.result["status"] == "completed"
        assert SceneMedia.objects.filter(project=project).count() == 4

    def test_full_run_all_media_types(self, make_user):
        user = make_user(username="exec_all")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.SCENE_MEDIA_GENERATION,
        )
        execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert job.result["count"] == 8
        types = set(SceneMedia.objects.values_list("media_type", flat=True))
        assert types == {"visual", "voice", "music", "subtitle"}


@pytest.mark.django_db
class TestExecutorFailureAndRetry:
    def test_failure_marks_job_failed_and_writes_no_media(self, make_user):
        user = make_user(username="exec_fail")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.SCENE_MEDIA_GENERATION,
        )
        original = tasks._provider
        tasks.set_provider(_FailingProvider())
        try:
            result = execute_job.delay(job.id).get()
        finally:
            tasks.set_provider(original)
        job.refresh_from_db()
        assert result["status"] == AsyncJob.Status.FAILED
        assert job.status == AsyncJob.Status.FAILED
        assert "media provider down" in job.error_message
        assert SceneMedia.objects.filter(project=project).count() == 0

    def test_retry_after_failure_completes_idempotently(self, make_user):
        user = make_user(username="exec_retry")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.SCENE_MEDIA_GENERATION,
        )
        # first run fails
        original = tasks._provider
        tasks.set_provider(_FailingProvider())
        try:
            execute_job.delay(job.id).get()
        finally:
            tasks.set_provider(original)
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED

        # retry marks retrying then re-run succeeds with the healthy provider
        retry_job(user, job)
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.RETRYING
        assert job.retry_count == 1

        result = execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert result["completed"] is True
        assert job.status == AsyncJob.Status.COMPLETED
        assert SceneMedia.objects.filter(project=project).count() == 8

        # running the handler again (another retry) does not duplicate media rows
        again = services.run_generation(job, provider=FakeSceneMediaProvider())
        assert again["count"] == 8
        assert SceneMedia.objects.filter(project=project).count() == 8

    def test_retries_are_bounded_by_max_retries(self, make_user):
        user = make_user(username="exec_bound")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.SCENE_MEDIA_GENERATION,
            status=AsyncJob.Status.FAILED,
            retry_count=3,  # == max_retries default
        )
        with pytest.raises(ValueError) as exc:
            retry_job(user, job)
        assert "Maximum retries exceeded" in str(exc.value)
