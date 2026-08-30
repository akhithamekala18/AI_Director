# -*- coding: utf-8 -*-
"""Character service layer tests (Phase 2D, Task 23 / Overview §20.1.4)."""
import pytest
from django.core.exceptions import ValidationError

from apps.character import services
from apps.character.models import Character, CharacterLibrary

from .helpers import FAKE_CHARACTERS, approved_script, make_project


def _char_with_id(cid, name="Maya"):
    """A stored character dict carrying a stable id (for library tests)."""
    return {
        "id": cid,
        "name": name,
        "age": "30s",
        "gender": "female",
        "appearance": {"hair_color": "brown"},
        "clothing": {"outfit": "field jacket"},
        "accessories": ["helmet"],
        "style": {"realism": "medium"},
    }


class TestGenerateCharacters:
    def test_generate_creates_and_reaches_review(self, make_user, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        user = make_user(username="svc_char")
        project = make_project(user)
        approved_script(user, project)

        character = services.generate_characters(user, project)
        character.refresh_from_db()
        assert character.team_id == user.memberships.first().team_id
        assert character.gate_state == Character.GateState.REVIEW
        assert len(character.characters) == 2

    def test_generate_requires_approved_script(self, make_user):
        user = make_user(username="svc_char2")
        project = make_project(user)
        with pytest.raises(ValidationError):
            services.generate_characters(user, project)

    def test_generate_after_approval_rejected(self, make_user):
        user = make_user(username="svc_char3")
        project = make_project(user)
        approved_script(user, project)
        character = Character.objects.create(
            project=project, team=project.team, gate_state=Character.GateState.APPROVED
        )
        with pytest.raises(ValidationError):
            services.generate_characters(user, project)
        assert character.gate_state == Character.GateState.APPROVED


class TestApproveCharacters:
    def _review_character(self, user, project, chars=None):
        script = approved_script(user, project)
        character = Character.objects.create(
            project=project,
            team=project.team,
            script=script,
            characters=chars if chars is not None else [_char_with_id("char_abc")],
            gate_state=Character.GateState.REVIEW,
        )
        return character

    def test_approve_requires_review_state(self, make_user):
        user = make_user(username="appr_char")
        project = make_project(user)
        approved_script(user, project)
        character = Character.objects.create(
            project=project, team=project.team, gate_state=Character.GateState.DRAFT
        )
        with pytest.raises(ValidationError):
            services.approve_character(user, character)

    def test_approve_requires_characters(self, make_user):
        user = make_user(username="appr_char2")
        project = make_project(user)
        character = self._review_character(user, project, chars=[])
        with pytest.raises(ValidationError):
            services.approve_character(user, character)

    def test_approve_sets_metadata_and_saves_library(self, make_user):
        user = make_user(username="appr_char3")
        project = make_project(user)
        character = self._review_character(user, project, chars=[_char_with_id("char_abc", "Maya")])
        services.approve_character(user, character)
        character.refresh_from_db()
        assert character.gate_state == Character.GateState.APPROVED
        assert character.approval_actor_id == user.id
        assert character.approval_at is not None

        entry = CharacterLibrary.objects.filter(character_id="char_abc").first()
        assert entry is not None
        assert entry.name == "Maya"
        assert entry.version == 1
        assert entry.team_id == character.team_id


class TestRequestChanges:
    def test_requires_reason(self, make_user):
        from apps.character.services import request_character_changes

        user = make_user(username="req_char")
        project = make_project(user)
        approved_script(user, project)
        character = Character.objects.create(
            project=project, team=project.team, gate_state=Character.GateState.REVIEW
        )
        with pytest.raises(ValidationError):
            request_character_changes(user, character, "   ")

    def test_requires_review_state(self, make_user):
        from apps.character.services import request_character_changes

        user = make_user(username="req_char2")
        project = make_project(user)
        approved_script(user, project)
        character = Character.objects.create(
            project=project, team=project.team, gate_state=Character.GateState.DRAFT
        )
        with pytest.raises(ValidationError):
            request_character_changes(user, character, "no")

    def test_requests_changes(self, make_user):
        from apps.character.services import request_character_changes

        user = make_user(username="req_char3")
        project = make_project(user)
        approved_script(user, project)
        character = Character.objects.create(
            project=project, team=project.team, gate_state=Character.GateState.REVIEW
        )
        request_character_changes(user, character, "make narrator friendlier")
        character.refresh_from_db()
        assert character.gate_state == Character.GateState.REVISION_REQUESTED
        assert character.rejection_reason == "make narrator friendlier"
