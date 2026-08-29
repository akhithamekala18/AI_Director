# -*- coding: utf-8 -*-
"""State machine unit tests (Development Plan Day 3 exit criteria)."""
import pytest

from apps.core.enums import ProjectLifecycle as S
from apps.core.state_machine import (
    can_transition,
    is_terminal,
    legal_transitions,
    pipeline_index,
    validate_transition,
)

_FORWARD = [
    (S.DRAFT, S.RESEARCHING),
    (S.RESEARCHING, S.RESEARCH_APPROVED),
    (S.RESEARCH_APPROVED, S.SCRIPTING),
    (S.SCRIPTING, S.SCRIPT_APPROVED),
    (S.SCRIPT_APPROVED, S.PRODUCING),
    (S.PRODUCING, S.VIDEO_APPROVED),
    (S.VIDEO_APPROVED, S.SCHEDULED),
    (S.SCHEDULED, S.PUBLISHED),
]


@pytest.mark.parametrize("source,target", _FORWARD)
def test_all_linear_forward_transitions_are_legal(source, target):
    assert can_transition(source, target)
    ok, error = validate_transition(source, target)
    assert ok, error


@pytest.mark.parametrize("source", list(S))
def test_archive_is_legal_from_every_non_archived_state(source):
    if source is S.ARCHIVED:
        assert is_terminal(source)
        assert not can_transition(source, S.ARCHIVED)
        return
    assert can_transition(source, S.ARCHIVED), f"archive from {source}"


def test_archived_is_terminal_and_has_no_legal_transitions():
    assert is_terminal(S.ARCHIVED)
    assert legal_transitions(S.ARCHIVED) == set()


@pytest.mark.parametrize("source,target", [
    (S.DRAFT, S.SCRIPTING),
    (S.DRAFT, S.PUBLISHED),
    (S.RESEARCH_APPROVED, S.DRAFT),
    (S.PUBLISHED, S.DRAFT),
    (S.SCRIPTING, S.RESEARCHING),  # no backward transitions
    (S.RESEARCHING, S.PRODUCING),   # cannot skip Research Approved
])
def test_illegal_transitions_are_rejected(source, target):
    assert not can_transition(source, target)
    ok, error = validate_transition(source, target)
    assert not ok
    assert error


def test_same_state_transition_is_rejected():
    ok, error = validate_transition(S.DRAFT, S.DRAFT)
    assert not ok


def test_pipeline_index_is_monotonic():
    indices = [pipeline_index(s) for s in _FORWARD]
    assert indices == sorted(indices)
    assert pipeline_index(S.ARCHIVED) is None
