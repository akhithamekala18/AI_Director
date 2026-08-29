# -*- coding: utf-8 -*-
"""Project lifecycle state machine (Backend-owned invariant, Development Plan
Day 3). Enforces the linear pipeline order from Project Overview §20.1.1 plus
the Archive terminal available from every non-archived state.

The linear pipeline is a product invariant (§41.2): no stage may be entered out
of order. Forward moves follow the pipeline; Archive is separately reachable
from any active state. Only the transitions returned here are legal.
"""

from apps.core.enums import ProjectLifecycle

_LINEAR = [
    ProjectLifecycle.DRAFT,
    ProjectLifecycle.RESEARCHING,
    ProjectLifecycle.RESEARCH_APPROVED,
    ProjectLifecycle.SCRIPTING,
    ProjectLifecycle.SCRIPT_APPROVED,
    ProjectLifecycle.PRODUCING,
    ProjectLifecycle.VIDEO_APPROVED,
    ProjectLifecycle.SCHEDULED,
    ProjectLifecycle.PUBLISHED,
]

# Legal forward transitions (linear pipeline).
_FORWARD = {
    ProjectLifecycle.DRAFT: ProjectLifecycle.RESEARCHING,
    ProjectLifecycle.RESEARCHING: ProjectLifecycle.RESEARCH_APPROVED,
    ProjectLifecycle.RESEARCH_APPROVED: ProjectLifecycle.SCRIPTING,
    ProjectLifecycle.SCRIPTING: ProjectLifecycle.SCRIPT_APPROVED,
    ProjectLifecycle.SCRIPT_APPROVED: ProjectLifecycle.PRODUCING,
    ProjectLifecycle.PRODUCING: ProjectLifecycle.VIDEO_APPROVED,
    ProjectLifecycle.VIDEO_APPROVED: ProjectLifecycle.SCHEDULED,
    ProjectLifecycle.SCHEDULED: ProjectLifecycle.PUBLISHED,
}

_ARCHIVED = ProjectLifecycle.ARCHIVED


def legal_transitions(state):
    """Return the set of states reachable from `state` in one legal step."""
    if state is None or state == _ARCHIVED:
        return set()
    targets = set()
    forward = _FORWARD.get(state)
    if forward is not None:
        targets.add(forward)
    # Archive is reachable from every non-archived state.
    targets.add(_ARCHIVED)
    return targets


def can_transition(state, target):
    return target in legal_transitions(state)


def validate_transition(state, target):
    """Return (ok, error_message)."""
    if state == target:
        return False, "transition to the same state is a no-op"
    if target not in legal_transitions(state):
        return False, f"illegal transition from {state!r} to {target!r}"
    return True, ""


def is_terminal(state):
    return state == _ARCHIVED


def pipeline_index(state):
    """Index in the canonical linear pipeline, or None for Archive."""
    if state in _LINEAR:
        return _LINEAR.index(state)
    return None
