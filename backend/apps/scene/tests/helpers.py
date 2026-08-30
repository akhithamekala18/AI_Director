# -*- coding: utf-8 -*-
"""Shared helpers for scene package tests."""
from apps.projects.models import Project


def make_project(user, topic="Volcanic eruptions", lifecycle_state="Draft"):
    """Create a project owned by `user` and scoped to their team."""
    return Project.objects.create(
        team=user.memberships.first().team,
        owner=user,
        topic=topic,
        lifecycle_state=lifecycle_state,
    )


def approved_script(user, project, scenes=None):
    """Create an APPROVED Script for a project (satisfies Gate 2).

    Builds the approved Research (G-1) then an approved Script (Gate 2) carrying
    a scene decomposition so the Scene Builder has scenes to map.
    """
    from apps.research.models import Research, ResearchSource
    from apps.script.models import Script

    research = Research.objects.create(project=project, team=project.team)
    ResearchSource.objects.create(
        research=research,
        url="https://example.org/volcanoes",
        title="Volcanoes Explained",
        snippet="An overview of volcanic eruption mechanisms.",
        credibility_score=0.9,
    )
    research.summary = "Volcanoes erupt when magma rises to the surface."
    research.gate_state = Research.GateState.APPROVED
    research.save()

    if scenes is None:
        scenes = [
            {
                "id": "s1",
                "heading": "Hook",
                "narration": "What causes a volcano to erupt?",
                "visual_notes": "Volcano wide shot, ash plume.",
            },
            {
                "id": "s2",
                "heading": "Core concepts",
                "narration": "Magma rises and builds pressure.",
                "visual_notes": "Cutaway diagram of magma chamber.",
            },
        ]

    return Script.objects.create(
        project=project,
        team=project.team,
        research=research,
        title="Volcanoes Explained",
        script="Volcanoes erupt when magma rises. Let's break it down.",
        narration="Welcome. Today we explore volcanic eruptions.",
        scenes=scenes,
        gate_state=Script.GateState.APPROVED,
    )


def approved_characters(user, project, script=None):
    """Create an APPROVED Character set (Gate 3) with stable ids.

    Characters carry stable ``char_*`` ids so the Scene Builder can reference
    them by identity (G-5) without needing a full library approval flow.
    """
    from apps.character.models import Character

    if script is None:
        from apps.script.models import Script

        script = Script.objects.filter(
            project=project, gate_state=Script.GateState.APPROVED
        ).first()

    return Character.objects.create(
        project=project,
        team=project.team,
        script=script,
        characters=[
            {
                "id": "char_volcanologist",
                "name": "Volcanologist Maya",
                "age": "30s",
                "gender": "female",
                "appearance": {"hair_color": "brown"},
                "clothing": {"outfit": "field jacket"},
                "accessories": ["helmet"],
                "style": {"realism": "medium"},
            },
            {
                "id": "char_narrator",
                "name": "Narrator Team",
                "age": "adult",
                "gender": "ambiguous",
                "appearance": {"hair_color": "dark"},
                "clothing": {"outfit": "studio casual"},
                "accessories": ["microphone"],
                "style": {"realism": "stylized"},
            },
        ],
        gate_state=Character.GateState.APPROVED,
    )
