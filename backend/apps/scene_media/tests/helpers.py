# -*- coding: utf-8 -*-
"""Shared helpers for scene media tests.

Reuses the frozen Phase 2C–2E helpers (approved Script Gate 2, approved
Character set Gate 3) and builds APPROVED / REVIEW / DRAFT / REVISION_REQUESTED
scene packages (Gate 4) so the media dependency can be tested in every state.
"""
from apps.scene import services as scene_services
from apps.scene.models import SceneBuilder
from apps.scene.tests.helpers import (  # noqa: F401
    approved_characters,
    approved_script,
    make_project,
)


def approved_scene_builder(user, project, scenes=None):
    """Build and approve a scene package (Gate 4 == approved)."""
    script = approved_script(user, project, scenes=scenes)
    approved_characters(user, project, script)
    builder = scene_services.build_scenes(user, project)
    scene_services.approve_scene_builder(user, builder)
    builder.refresh_from_db()
    assert builder.gate_state == SceneBuilder.GateState.APPROVED
    return builder


def review_scene_builder(user, project, scenes=None):
    """Build a scene package into Gate 4 `review` (not approved)."""
    script = approved_script(user, project, scenes=scenes)
    approved_characters(user, project, script)
    builder = scene_services.build_scenes(user, project)
    builder.refresh_from_db()
    assert builder.gate_state == SceneBuilder.GateState.REVIEW
    return builder


def revision_scene_builder(user, project, scenes=None):
    """Build a scene package into Gate 4 `revision_requested`."""
    builder = review_scene_builder(user, project, scenes=scenes)
    scene_services.request_scene_changes(user, builder, "needs a rewrite")
    builder.refresh_from_db()
    assert builder.gate_state == SceneBuilder.GateState.REVISION_REQUESTED
    return builder


def draft_scene_builder(user, project):
    """Create a SceneBuilder in the initial Gate 4 `draft` state (no build)."""
    return SceneBuilder.objects.create(
        project=project, team=project.team, gate_state=SceneBuilder.GateState.DRAFT
    )
