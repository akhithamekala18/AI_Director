# -*- coding: utf-8 -*-
"""End-to-end runtime verification for Phase 2C (Development Plan Day 22).

Exercises the full Gate 2 flow against the running ORM using a deterministic
FAKE provider (no external API). Mirrors the STEP 32 runtime-verification
scenario for the Script app and Gate 2.

REAL OpenAI execution is NOT AVAILABLE here; runtime verification is performed
strictly with the provider-agnostic fake adapter (real provider: NOT VERIFIED).
"""
import pytest

from apps.accounts.models import Team
from apps.ai_orchestration.models import AsyncJob

from .helpers import FAKE_SCRIPT, approved_research, make_project


@pytest.mark.django_db
class TestPhase2CRuntime:
    def test_full_gate2_flow(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        from apps.script import services
        from apps.script.models import Script

        user = make_user(username="runtime_user")
        project = make_project(user)
        approved_research(user, project)

        script = services.generate_script(user, project)
        script.refresh_from_db()

        # Script persisted with correct project/team and state.
        assert script.id
        assert script.team_id == user.memberships.first().team_id
        assert script.gate_state == Script.GateState.REVIEW

        # AsyncJob persisted & completed.
        job = AsyncJob.objects.filter(
            project=project, job_type=AsyncJob.JobType.SCRIPT_GENERATION
        ).order_by("-id").first()
        assert job is not None
        assert job.status == AsyncJob.Status.COMPLETED

        # Script package fields populated.
        assert script.title
        assert script.script
        assert script.narration
        assert len(script.scenes) == 2
        assert script.captions == [
            "Quantum gravity = general relativity + quantum mechanics"
        ]
        assert "#quantumgravity" in script.hashtags

        # Gate 2 approve works.
        services.approve_script(user, script)
        script.refresh_from_db()
        assert script.gate_state == Script.GateState.APPROVED
        assert script.approval_actor_id == user.id
        assert script.approval_at is not None

    def test_cross_team_script_isolated(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        from apps.script import services
        from apps.script.services import get_script

        user = make_user(username="iso_owner")
        project = make_project(user)
        approved_research(user, project)
        services.generate_script(user, project)

        outsider = make_user(username="iso_out")
        outsider.memberships.create(team=Team.objects.create(name="Other Team"), role="Editor")
        assert get_script(outsider, project) is None
        # project not even visible to outsider.
        from apps.projects.services import get_project
        assert get_project(outsider, project.id) is None

    def test_provider_failure_fails_job_and_keeps_gate(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script",
            lambda research: {**FAKE_SCRIPT, "script": ""},
        )
        from apps.script import services
        from apps.script.models import Script

        user = make_user(username="fail_user")
        project = make_project(user)
        approved_research(user, project)

        services.generate_script(user, project)
        job = AsyncJob.objects.filter(
            project=project, job_type=AsyncJob.JobType.SCRIPT_GENERATION
        ).order_by("-id").first()
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        script = Script.objects.get(project=project)
        script.refresh_from_db()
        # eager execution: generation failed before reaching review
        assert script.gate_state != Script.GateState.REVIEW
