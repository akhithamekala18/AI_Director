# -*- coding: utf-8 -*-
"""Autouse fixture guaranteeing the character_detection executor is registered.

Phase 2A's test_unhandled_job_type_fails_deterministically deliberately pops
registered executors from the shared JOB_EXECUTORS registry. In a full-suite run
that leak could otherwise remove executors Phase 2B/2C/2D legitimately register,
causing spurious "no executor configured" failures.

This autouse fixture re-registers the real executor before every character test,
restoring the registry entry. It only applies to tests under apps/character and
does not weaken the executor's state-machine contract.
"""
import pytest

from apps.ai_orchestration import tasks as orch_tasks
from apps.character.tasks import JOB_TYPE, run_character_detection


@pytest.fixture(autouse=True)
def _ensure_character_executor_registered():
    orch_tasks.JOB_EXECUTORS[JOB_TYPE] = run_character_detection
    yield
