# -*- coding: utf-8 -*-
"""Shared fixtures for scheduler tests (Task 38)."""
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.fixture
def user(make_user):
    return make_user(username="sched_user", role="Creator")


@pytest.fixture
def team(user):
    return user.memberships.first().team


@pytest.fixture
def project(user, team):
    from apps.projects.models import Project
    return Project.objects.create(
        topic="Test Scheduler Project",
        team=team,
        owner=user,
    )


@pytest.fixture
def auth_client(make_user, user):
    """Authenticated APIClient for the user."""
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client


@pytest.fixture
def outsider_client(make_user):
    """Authenticated client for a user NOT in the project's team."""
    outsider = make_user(username="sched_outsider", role="Creator")
    token, _ = Token.objects.get_or_create(user=outsider)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = outsider
    return client


@pytest.fixture
def approved_video(user, project):
    """Create an approved video asset (requires approved scene package)."""
    from apps.scene import services as scene_services
    script = _approved_script(user, project)
    _approved_characters(user, project, script)
    builder = scene_services.build_scenes(user, project)
    scene_services.approve_scene_builder(user, builder)
    builder.refresh_from_db()
    from apps.video.services import request_video
    video = request_video(user, project, "YouTube")
    return video


@pytest.fixture
def approved_preview(user, project, approved_video):
    """Generate and approve a preview for YouTube."""
    from apps.preview.services import request_preview, approve_preview
    preview = request_preview(user, project, "YouTube")
    approve_preview(user, preview)
    return preview


def _approved_script(user, project):
    from apps.research.models import Research, ResearchSource
    from apps.script.models import Script
    research = Research.objects.create(project=project, team=project.team)
    ResearchSource.objects.create(
        research=research, url="https://example.org/test",
        title="Test Source", snippet="Test snippet.", credibility_score=0.9,
    )
    research.summary = "Test research summary."
    research.gate_state = Research.GateState.APPROVED
    research.save()
    scenes = [
        {"id": "s1", "heading": "Hook", "narration": "Hook narration.", "visual_notes": "Hook visual."},
        {"id": "s2", "heading": "Body", "narration": "Body narration.", "visual_notes": "Body visual."},
    ]
    return Script.objects.create(
        project=project, team=project.team, research=research,
        title="Test Script", script="Test script body.", narration="Test narration.",
        scenes=scenes, gate_state=Script.GateState.APPROVED,
    )


def _approved_characters(user, project, script):
    from apps.character.models import Character
    return Character.objects.create(
        project=project, team=project.team, script=script,
        characters=[{"id": "char1", "name": "Test Char", "age": "30s", "gender": "female"}],
        gate_state=Character.GateState.APPROVED,
    )
