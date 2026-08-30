# -*- coding: utf-8 -*-
"""Shared helpers for character tests."""
from apps.projects.models import Project


def make_project(user, topic="Volcanic eruptions", lifecycle_state="Draft"):
    """Create a project owned by `user` and scoped to their team."""
    return Project.objects.create(
        team=user.memberships.first().team,
        owner=user,
        topic=topic,
        lifecycle_state=lifecycle_state,
    )


def approved_script(user, project):
    """Create an APPROVED Script for a project (satisfies G-2).

    Mirrors script.tests.helpers.approved_research: builds the approved
    Research (G-1) then an approved Script (Gate 2) so character detection can
    proceed. Bypasses generation for test convenience.
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

    return Script.objects.create(
        project=project,
        team=project.team,
        research=research,
        title="Volcanoes Explained",
        script="Volcanoes erupt when magma rises. Let's break it down.",
        narration="Welcome. Today we explore volcanic eruptions.",
        gate_state=Script.GateState.APPROVED,
    )


FAKE_CHARACTERS = {
    "characters": [
        {
            "name": "Volcanologist Maya",
            "age": "30s",
            "gender": "female",
            "appearance": {
                "face_shape": "oval",
                "hair_style": "wavy",
                "hair_color": "brown",
                "eyes": "hazel",
                "skin_tone": "light",
            },
            "clothing": {
                "outfit": "field jacket",
                "colors": ["khaki", "green"],
                "style": "practical",
            },
            "accessories": ["safety helmet", "notebook"],
            "style": {
                "illustrative_style": "semi-realistic",
                "realism": "medium",
                "palette": ["earth", "amber"],
            },
        },
        {
            "name": "Narrator Team",
            "age": "adult",
            "gender": "ambiguous",
            "appearance": {
                "face_shape": "round",
                "hair_style": "short",
                "hair_color": "dark",
                "eyes": "brown",
                "skin_tone": "medium",
            },
            "clothing": {
                "outfit": "studio casual",
                "colors": ["navy", "white"],
                "style": "modern",
            },
            "accessories": ["microphone"],
            "style": {
                "illustrative_style": "flat",
                "realism": "stylized",
                "palette": ["blue", "grey"],
            },
        },
    ],
    "cost": 0.03,
}
