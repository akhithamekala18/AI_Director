# -*- coding: utf-8 -*-
"""Script executor tests (Phase 2C integration with Phase 2A AsyncJob).

Confirms a `script_generation` executor is registered with the Phase 2A
JOB_EXECUTORS registry and that execute_job drives the Script artifact from
`generating` to `review` (with title + script + narration), failing
deterministically when the produced artifact is invalid.
"""
import pytest

from apps.ai_orchestration import tasks as orch_tasks
from apps.ai_orchestration.models import AsyncJob
from apps.script.models import Script
from apps.script.tasks import JOB_TYPE, run_script_generation

from .helpers import FAKE_SCRIPT, approved_research, make_project


@pytest.mark.django_db
class TestExecutorRegistration:
    def test_executor_registered(self, make_user):
        assert JOB_TYPE == AsyncJob.JobType.SCRIPT_GENERATION
        assert orch_tasks.JOB_EXECUTORS.get(JOB_TYPE) is run_script_generation


@pytest.mark.django_db
class TestExecutorExecution:
    def _job(self, user, project, script):
        return AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=JOB_TYPE,
            metadata={"script_id": script.id},
        )

    def test_drives_script_to_review(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        user = make_user(username="exec_script")
        project = make_project(user)
        research = approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team, research=research)
        # The service moves the artifact to generating before the job runs.
        script.transition_to(Script.GateState.GENERATING)
        script.save(update_fields=["gate_state"])
        job = self._job(user, project, script)

        orch_tasks.execute_job.delay(job.id).get()

        job.refresh_from_db()
        script.refresh_from_db()
        assert job.status == AsyncJob.Status.COMPLETED
        assert script.gate_state == Script.GateState.REVIEW
        assert script.title
        assert script.script
        assert script.narration
        assert len(script.scenes) == 2
        assert script.captions == ["Quantum gravity = general relativity + quantum mechanics"]
        assert "#quantumgravity" in script.hashtags
        assert job.result["scene_count"] == 2

    def test_empty_title_fails_job(self, make_user, monkeypatch):
        bad = dict(FAKE_SCRIPT, title="")
        monkeypatch.setattr("apps.script.engine.gather_script", lambda research: bad)
        user = make_user(username="exec_script2")
        project = make_project(user)
        research = approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team, research=research)
        job = self._job(user, project, script)

        orch_tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        script.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        assert script.gate_state == Script.GateState.DRAFT

    def test_empty_script_fails_job(self, make_user, monkeypatch):
        bad = dict(FAKE_SCRIPT, script="")
        monkeypatch.setattr("apps.script.engine.gather_script", lambda research: bad)
        user = make_user(username="exec_script3")
        project = make_project(user)
        research = approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team, research=research)
        job = self._job(user, project, script)

        orch_tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED

    def test_missing_empty_narration_fails_job(self, make_user, monkeypatch):
        bad = dict(FAKE_SCRIPT, narration="")
        monkeypatch.setattr("apps.script.engine.gather_script", lambda research: bad)
        user = make_user(username="exec_script4")
        project = make_project(user)
        research = approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team, research=research)
        job = self._job(user, project, script)

        orch_tasks.execute_job.delay(job.id).get()
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
