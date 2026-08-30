# -*- coding: utf-8 -*-
"""Autouse fixture guaranteeing the research_generation executor is registered.

Phase 2A's test_unhandled_job_type_fails_deterministically deliberately pops
`research_generation` from the shared JOB_EXECUTORS registry and does not
restore it. In a full-suite run (ai_orchestration is collected before research)
that leak would otherwise remove the executor Phase 2B legitimately registers,
causing spurious "no executor configured" failures.

This autouse fixture re-registers the real executor before every research test,
restoring the registry entry that Phase 2A's test removes. It only applies to
tests under apps/research and does not weaken the executor's state-machine
contract.
"""
import pytest

from apps.ai_orchestration import tasks as orch_tasks
from apps.research.tasks import JOB_TYPE, run_research_generation


@pytest.fixture(autouse=True)
def _ensure_research_executor_registered():
    orch_tasks.JOB_EXECUTORS[JOB_TYPE] = run_research_generation
    yield
