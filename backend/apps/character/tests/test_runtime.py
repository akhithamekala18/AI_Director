# -*- coding: utf-8 -*-
"""End-to-end runtime verification for Phase 2D (Task 23).

Exercises the full Gate 3 flow against the running ORM using a deterministic
FAKE provider (no external API). Mirrors the STEP 32/33 runtime-verification
scenario for the Research/Script apps and Gate 3.

This demonstrates a successful detection -> review -> approve cycle (which also
populates the reusable CharacterLibrary), a cross-project reuse preserving
identity (G-5), and deterministic failure when detection yields nothing.

REAL provider execution is NOT AVAILABLE here; runtime verification is
performed strictly with the provider-agnostic fake adapter (real provider:
NOT VERIFIED).
"""
import pytest

from apps.accounts.models import Team
from apps.ai_orchestration.models import AsyncJob
from apps.character.models import CharacterLibrary

from .helpers import FAKE_CHARACTERS, approved_script, make_project


@pytest.mark.django_db
class TestPhase2DRuntime:
    def test_full_gate3_flow_with_reuse(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): {
                "characters": [
                    {"id": f"char_{idx}", **dict(c)}
                    for idx, c in enumerate(FAKE_CHARACTERS["characters"])
                ],
                "cost": FAKE_CHARACTERS["cost"],
            },
        )
        from apps.character import services
        from apps.character.models import Character

        user = make_user(username="char_runtime")
        project = make_project(user)
        approved_script(user, project)

        character = services.generate_characters(user, project)
        character.refresh_from_db()

        # CharacterSet persisted with correct project/team and state.
        assert character.id
        assert character.team_id == user.memberships.first().team_id
        assert character.gate_state == Character.GateState.REVIEW

        # AsyncJob persisted & completed.
        job = (
            AsyncJob.objects.filter(
                project=project, job_type=AsyncJob.JobType.CHARACTER_DETECTION
            )
            .order_by("-id")
            .first()
        )
        assert job is not None
        assert job.status == AsyncJob.Status.COMPLETED

        # Detected characters populated with attributes.
        assert len(character.characters) == 2
        first = character.characters[0]
        assert first["age"]
        assert first["gender"]
        assert first["appearance"]
        assert first["clothing"]
        assert "safety helmet" in first["accessories"]

        # Gate 3 approve works and populates the library (with stable ids).
        ids = [c["id"] for c in character.characters]
        assert ids and all(i.startswith("char_") for i in ids)
        services.approve_character(user, character)
        character.refresh_from_db()
        assert character.gate_state == Character.GateState.APPROVED
        assert character.approval_actor_id == user.id
        assert character.approval_at is not None
        assert CharacterLibrary.objects.filter(team=character.team).count() == 2

        # Cross-project reuse preserves identity (G-5).
        project_b = make_project(user, topic="Second topic")
        approved_script(user, project_b)
        entry = CharacterLibrary.objects.filter(character_id=ids[0]).first()
        reused = services.reuse_character(user, project_b, entry)
        reused.refresh_from_db()
        same = next(c for c in reused.characters if c["id"] == ids[0])
        assert same["age"] == entry.age
        assert same["gender"] == entry.gender
        assert same["clothing"] == entry.clothing

    def test_cross_team_character_isolated(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        from apps.character import services
        from apps.character.services import get_character

        user = make_user(username="iso_owner")
        project = make_project(user)
        approved_script(user, project)
        services.generate_characters(user, project)

        outsider = make_user(username="iso_out")
        outsider.memberships.create(
            team=Team.objects.create(name="Other Team"), role="Editor"
        )
        assert get_character(outsider, project) is None
        from apps.projects.services import get_project

        assert get_project(outsider, project.id) is None

    def test_provider_failure_fails_job_and_keeps_gate(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): {"characters": [], "cost": 0},
        )
        from apps.character import services
        from apps.character.models import Character

        user = make_user(username="char_fail")
        project = make_project(user)
        approved_script(user, project)

        services.generate_characters(user, project)
        job = (
            AsyncJob.objects.filter(
                project=project, job_type=AsyncJob.JobType.CHARACTER_DETECTION
            )
            .order_by("-id")
            .first()
        )
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.FAILED
        character = Character.objects.get(project=project)
        character.refresh_from_db()
        # eager execution: detection failed before reaching review
        assert character.gate_state != Character.GateState.REVIEW
