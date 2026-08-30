# -*- coding: utf-8 -*-
"""Tests for the Celery task substrate (Phase 2A F10, DEFECT 3).

Runs in eager mode (CELERY_TASK_ALWAYS_EAGER=True) so no real worker/Redis is
required. Uses a registered fake executor to prove state transitions; no real
AI provider is called.
"""
import pytest

from apps.ai_orchestration import tasks
from apps.ai_orchestration.models import AsyncJob


@pytest.mark.django_db
class TestExecuteJobTask:
    """Drive AsyncJob through the Celery task state machine."""

    def _make_job(self, user, project, status=AsyncJob.Status.PENDING):
        return AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=status,
        )

    def test_pending_runs_and_completes(self, make_user):
        from apps.projects.models import Project
        user = make_user(username="task_user")
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._make_job(user, project)

        def handler(job):
            job.progress = 1.0
            return {"ok": True}

        tasks.JOB_EXECUTORS["research_generation"] = handler
        try:
            result = tasks.execute_job.delay(job.id).get()
        finally:
            tasks.JOB_EXECUTORS.pop("research_generation", None)

        job.refresh_from_db()
        assert result["completed"] is True
        assert job.status == AsyncJob.Status.COMPLETED
        assert job.started_at is not None
        assert job.completed_at is not None

    def test_unhandled_job_type_fails_deterministically(self, make_user):
        from apps.projects.models import Project
        user = make_user(username="task_user2")
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._make_job(user, project)
        # ensure no handler is registered for the job type
        tasks.JOB_EXECUTORS.pop("research_generation", None)

        result = tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert result["status"] == AsyncJob.Status.FAILED
        assert job.status == AsyncJob.Status.FAILED
        assert "no executor configured" in job.error_message

    def test_handler_error_marks_job_failed(self, make_user):
        from apps.projects.models import Project
        user = make_user(username="task_user3")
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._make_job(user, project)

        def exploding_handler(job):
            raise RuntimeError("boom")

        tasks.JOB_EXECUTORS["research_generation"] = exploding_handler
        try:
            result = tasks.execute_job.delay(job.id).get()
        finally:
            tasks.JOB_EXECUTORS.pop("research_generation", None)

        job.refresh_from_db()
        assert result["status"] == AsyncJob.Status.FAILED
        assert job.status == AsyncJob.Status.FAILED
        assert job.error_message == "boom"

    def test_cannot_start_from_terminal_or_invalid_state(self, make_user):
        from apps.projects.models import Project
        user = make_user(username="task_user4")
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._make_job(user, project, status=AsyncJob.Status.COMPLETED)
        result = tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert result["started"] is False
        assert job.status == AsyncJob.Status.COMPLETED  # unharmed

    def test_missing_job_degrades_gracefully(self, make_user):
        result = tasks.execute_job.delay(999999).get()
        assert result["status"] == "unknown"

    def test_task_is_registered_with_expected_name(self):
        assert tasks.execute_job.name == "apps.ai_orchestration.tasks.execute_job"
