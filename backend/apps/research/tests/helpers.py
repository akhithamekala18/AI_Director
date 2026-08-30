# -*- coding: utf-8 -*-
"""Shared helpers for research tests."""
from apps.projects.models import Project


def make_project(user, topic="Quantum gravity", lifecycle_state="Draft"):
    """Create a project owned by `user` and scoped to their team."""
    return Project.objects.create(
        team=user.memberships.first().team,
        owner=user,
        topic=topic,
        lifecycle_state=lifecycle_state,
    )


FAKE_RESEARCH = {
    "summary": "Quantum gravity reconciles general relativity with quantum "
    "mechanics.",
    "sources": [
        {
            "url": "https://example.org/quantum-gravity",
            "title": "Quantum Gravity Explained",
            "snippet": "An overview of quantum gravity research.",
            "credibility_score": 0.9,
        }
    ],
    "gaps": [
        {
            "gap_type": "contradiction",
            "description": "Two sources disagree on the role of time.",
            "source_a": "Source A",
            "source_b": "Source B",
        }
    ],
    "cost": 0.03,
}
