# -*- coding: utf-8 -*-
"""Shared helpers for script tests."""
from apps.projects.models import Project


def make_project(user, topic="Quantum gravity", lifecycle_state="Draft"):
    """Create a project owned by `user` and scoped to their team."""
    return Project.objects.create(
        team=user.memberships.first().team,
        owner=user,
        topic=topic,
        lifecycle_state=lifecycle_state,
    )


def approved_research(user, project):
    """Create an approved Research artifact for a project (satisfies G-1)."""
    from apps.research.models import Research, ResearchSource

    research = Research.objects.create(project=project, team=project.team)
    ResearchSource.objects.create(
        research=research,
        url="https://example.org/quantum-gravity",
        title="Quantum Gravity Explained",
        snippet="An overview of quantum gravity research.",
        credibility_score=0.9,
    )
    research.summary = "Quantum gravity reconciles general relativity with "
    "quantum mechanics."
    research.gate_state = Research.GateState.APPROVED
    research.save()
    return research


FAKE_SCRIPT = {
    "title": "Quantum Gravity Explained",
    "outline": "1. Hook. 2. Core concepts. 3. Implications.",
    "script": "Quantum gravity reconciles general relativity with quantum "
    "mechanics. Let's break it down.",
    "narration": "Welcome back. Today we explore quantum gravity and why it "
    "matters.",
    "scenes": [
        {
            "id": "s1",
            "heading": "Hook",
            "narration": "What is quantum gravity?",
            "visual_notes": "Fast cuts, space imagery.",
        },
        {
            "id": "s2",
            "heading": "Core concepts",
            "narration": "Relativity meets quantum mechanics.",
            "visual_notes": "Diagrams.",
        },
    ],
    "captions": ["Quantum gravity = general relativity + quantum mechanics"],
    "hashtags": ["#quantumgravity", "#physics"],
    "cost": 0.03,
}
