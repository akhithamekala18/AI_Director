# -*- coding: utf-8 -*-
"""Research executor tests (Phase 2B integration with Phase 2A AsyncJob).

Confirms a `research_generation` executor is registered with the Phase 2A
JOB_EXECUTORS registry and that execute_job drives the Research artifact from
`generating` to `review` (with summary + >= 1 source), failing deterministically
when the produced artifact is invalid.
"""
import pytest

from apps.ai_orchestration import tasks as orch_tasks
from apps.ai_orchestration.models import AsyncJob
from apps.research.models import Research
from apps.research.tasks import JOB_TYPE, run_research_generation

from .helpers import FAKE_RESEARCH, make_project


@pytest.mark.django_db
class TestExecutorRegistration:
    def test_executor_registered(self):
        assert JOB_TYPE == AsyncJob.JobType.RESEARCH_GENERATION
        assert orch_tasks.JOB_EXECUTORS.get(JOB_TYPE) is run_research_generation


@pytest.mark.django_db
class TestExecutorExecution:
    def _job(self, user, project, research):
        return AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=JOB_TYPE,
            metadata={"research_id": research.id},
        )

    def test_drives_research_to_review(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        user = make_user(username="exec_user")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        # The service (generate_research) moves the artifact to generating before
        # the job runs; mirror that precondition here.
        research.transition_to(Research.GateState.GENERATING)
        research.save(update_fields=["gate_state"])
        job = self._job(user, project, research)

        orch_tasks.execute_job.delay(job.id).get()

        job.refresh_from_db()
        research.refresh_from_db()
        assert job.status == AsyncJob.Status.COMPLETED
        assert research.gate_state == Research.GateState.REVIEW
        assert research.summary
        assert research.sources.count() >= 1
        assert research.gaps.count() == 1
        assert job.result["source_count"] == 1

    def test_empty_summary_fails_job(self, make_user, monkeypatch):
        bad = dict(FAKE_RESEARCH, summary="")
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: bad
        )
        user = make_user(username="exec_user2")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        job = self._job(user, project, research)

        orch_tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        research.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        assert research.gate_state == Research.GateState.DRAFT

    def test_no_sources_fails_job(self, make_user, monkeypatch):
        bad = dict(FAKE_RESEARCH, sources=[])
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: bad
        )
        user = make_user(username="exec_user3")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        job = self._job(user, project, research)

        orch_tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        assert research.gate_state == Research.GateState.DRAFT
