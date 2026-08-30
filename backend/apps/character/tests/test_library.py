# -*- coding: utf-8 -*-
"""Character Library tests: versioning, cross-project reuse (G-5), isolation.

Validates the Phase 2D / Task 23 library requirements:
- characters are stored by a stable character_id and versioned (G-5),
- the same character_id yields consistent attributes across projects,
- a version change is recorded when a character's attributes change,
- reuse is strictly scoped to the owning team (team/char isolation).
"""
import pytest
from django.core.exceptions import ValidationError

from apps.character import services
from apps.character.models import Character, CharacterLibrary, current_library_version

from .helpers import approved_script, make_project


def _attrs(age="30s", hair="brown"):
    return {
        "name": "Maya",
        "age": age,
        "gender": "female",
        "appearance": {"hair_color": hair},
        "clothing": {"outfit": "field jacket"},
        "accessories": ["helmet"],
        "style": {"realism": "medium"},
    }


def _char_with_id(cid, **overrides):
    return {"id": cid, **_attrs(**overrides)}


def _review_set(user, project, cid, **overrides):
    script = approved_script(user, project)
    return Character.objects.create(
        project=project,
        team=project.team,
        script=script,
        characters=[_char_with_id(cid, **overrides)],
        gate_state=Character.GateState.REVIEW,
    )


class TestLibraryVersioning:
    def test_reapproval_increments_library_version(self, make_user):
        user = make_user(username="lib_user")
        project_a = make_project(user, topic="A")
        project_b = make_project(user, topic="B")

        services.approve_character(user, _review_set(user, project_a, "char_abc", age="30s"))
        assert current_library_version(project_a.team, "char_abc") == 1

        # A second project approves the same logical character with changed
        # attributes -> a new version is recorded under the same stable id.
        services.approve_character(
            user, _review_set(user, project_b, "char_abc", age="50s", hair="grey")
        )
        assert current_library_version(project_a.team, "char_abc") == 2

        rows = CharacterLibrary.objects.filter(
            team=project_a.team, character_id="char_abc"
        ).order_by("version")
        versions = list(rows.values_list("version", "age", "appearance__hair_color"))
        assert [v[0] for v in versions] == [1, 2]
        assert [v[1] for v in versions] == ["30s", "50s"]
        assert [v[2] for v in versions] == ["brown", "grey"]


class TestReuseIdentityPreservation:
    def test_reuse_preserves_identical_attributes(self, make_user):
        user = make_user(username="reuse_owner")
        project_a = make_project(user, topic="A")
        project_b = make_project(user, topic="B")

        services.approve_character(
            user, _review_set(user, project_a, "char_xyz", age="40s")
        )
        entry = (
            CharacterLibrary.objects.filter(
                team=project_a.team, character_id="char_xyz"
            )
            .order_by("-version")
            .first()
        )

        result = services.reuse_character(user, project_b, entry)
        result.refresh_from_db()

        reused = next(c for c in result.characters if c.get("id") == "char_xyz")
        # G-5: same character_id -> same attributes across projects.
        assert reused["id"] == entry.character_id
        assert reused["name"] == entry.name
        assert reused["age"] == entry.age
        assert reused["gender"] == entry.gender
        assert reused["appearance"] == entry.appearance
        assert reused["clothing"] == entry.clothing
        assert reused["accessories"] == entry.accessories
        assert reused["style"] == entry.style

    def test_reuse_of_other_team_rejected(self, make_user):
        owner = make_user(username="reuse_own2")
        outsider = make_user(username="reuse_out2", role="Editor")
        from apps.accounts.models import Team

        other_team = Team.objects.create(name="Other Team")
        outsider.memberships.create(team=other_team, role="Editor")

        project_a = make_project(owner, topic="A")
        services.approve_character(
            owner, _review_set(owner, project_a, "char_zzz", age="20s")
        )
        entry = CharacterLibrary.objects.filter(character_id="char_zzz").first()

        with pytest.raises(ValidationError):
            services.reuse_character(outsider, project_a, entry)


class TestLibraryTeamIsolation:
    def test_library_scoped_to_team(self, make_user):
        owner = make_user(username="lib_own3")
        outsider = make_user(username="lib_out3", role="Editor")
        from apps.accounts.models import Team

        outside_team = Team.objects.create(name="Out Team")
        outsider.memberships.create(team=outside_team, role="Editor")

        project_a = make_project(owner, topic="A")
        services.approve_character(
            owner, _review_set(owner, project_a, "char_iso", age="30s")
        )

        # same team sees the entry
        team_lib = services.list_library(owner, project_a)
        assert any(e.character_id == "char_iso" for e in team_lib)

        # outsider (different team, no access to project) sees only their own
        assert services.list_library(outsider, project_a) == []
