# -*- coding: utf-8 -*-
"""Character executor tests (Phase 2D integration with Phase 2A AsyncJob).

Confirms a `character_detection` executor is registered with the Phase 2A
JOB_EXECUTORS registry and that execute_job drives the Character artifact from
`generating` to `review` (with at least one character), failing
deterministically when detection produces no usable characters.
"""
import pytest

from apps.ai_orchestration import tasks as orch_tasks
from apps.ai_orchestration.models import AsyncJob
from apps.character.models import Character
from apps.character.tasks import JOB_TYPE, run_character_detection

from .helpers import FAKE_CHARACTERS, approved_script, make_project


@pytest.mark.django_db
class TestExecutorRegistration:
    def test_executor_registered(self, make_user):
        assert JOB_TYPE == AsyncJob.JobType.CHARACTER_DETECTION
        assert orch_tasks.JOB_EXECUTORS.get(JOB_TYPE) is run_character_detection


@pytest.mark.django_db
class TestExecutorExecution:
    def _job(self, user, project, character):
        return AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=JOB_TYPE,
            metadata={"character_id": character.id},
        )

    def _detecting(self, user, project):
        script = approved_script(user, project)
        character = Character.objects.create(
            project=project, team=project.team, script=script
        )
        character.transition_to(Character.GateState.GENERATING)
        character.save(update_fields=["gate_state"])
        return character

    def test_drives_character_to_review(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        user = make_user(username="exec_char")
        project = make_project(user)
        character = self._detecting(user, project)
        job = self._job(user, project, character)

        orch_tasks.execute_job.delay(job.id).get()

        job.refresh_from_db()
        character.refresh_from_db()
        assert job.status == AsyncJob.Status.COMPLETED
        assert character.gate_state == Character.GateState.REVIEW
        assert len(character.characters) == 2
        assert character.version == 2
        assert job.result["character_count"] == 2

    def test_empty_characters_fails_job(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): {"characters": [], "cost": 0},
        )
        user = make_user(username="exec_char2")
        project = make_project(user)
        character = self._detecting(user, project)
        job = self._job(user, project, character)

        orch_tasks.execute_job.delay(job.id).get()

        job.refresh_from_db()
        character.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        assert character.gate_state == Character.GateState.GENERATING

    def test_missing_script_fails_job(self, make_user, monkeypatch):
        user = make_user(username="exec_char3")
        project = make_project(user)
        character = Character.objects.create(project=project, team=project.team, script=None)
        character.transition_to(Character.GateState.GENERATING)
        character.save(update_fields=["gate_state"])
        job = self._job(user, project, character)

        orch_tasks.execute_job.delay(job.id).get()

        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
