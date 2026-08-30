# -*- coding: utf-8 -*-
"""Scene Builder runtime verification (Phase 2E, Task 24).

Phase 2E is a synchronous, deterministic mapping step over already-approved
artifacts; it invokes **no AI provider**. Therefore the real-provider runtime
verification is NOT APPLICABLE / NOT VERIFIED. This module exercises the full
end-to-end synchronous path — approved Script (Gate 2) + approved Character set
(Gate 3) -> Scene Builder -> Gate 4 review -> approval — exactly as it would run
in production but free of any external API dependency.
"""
import pytest

from apps.scene import services
from apps.scene.models import SceneBuilder

from .helpers import approved_characters, approved_script, make_project


@pytest.mark.django_db
class TestEndToEndSceneFlow:
    def test_concept_to_approved_scene_package_without_provider(self, make_user):
        user = make_user(username="runtime_scene")
        project = make_project(user)

        # Gate 2: approved Script with scene decomposition.
        script = approved_script(user, project)
        assert script.gate_state == "approved"

        # Gate 3: approved Character set with stable ids.
        characters = approved_characters(user, project, script)
        assert characters.gate_state == "approved"

        # Scene Builder (synchronous, deterministic): draft -> review.
        builder = services.build_scenes(user, project)
        assert builder.gate_state == SceneBuilder.GateState.REVIEW
        assert len(builder.scenes) == 2
        assert all(s["characters"] for s in builder.scenes)
        assert {s["id"] for s in builder.scenes} == {"s1", "s2"}

        # Gate 4 approval.
        services.approve_scene_builder(user, builder)
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.APPROVED
        assert builder.approval_actor_id == user.id
