# -*- coding: utf-8 -*-
"""Character detection executor (Phase 2D, Task 23).

Integrates character detection with the Phase 2A AsyncJob substrate: a
`character_detection` executor is registered via `register_executor()` so that
`execute_job` drives the job through pending -> running -> completed/failed while
the executor detects characters from the approved Script and moves Gate 3 from
`generating` to `review`.

Detection uses only the provider-agnostic engine (apps.character.engine), so no
live API credentials are required to exercise the flow (real provider execution
is NOT AVAILABLE here; runtime verification uses a fake adapter).
"""
from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.services import create_job
from apps.ai_orchestration.tasks import execute_job, register_executor
from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from . import engine
from .models import Character

JOB_TYPE = AsyncJob.JobType.CHARACTER_DETECTION


def enqueue_character_job(user, project, character_set):
    """Create and dispatch a character_detection AsyncJob for a Character row.

    Returns the created AsyncJob. In eager (test) mode the task executes
    synchronously; in production it is delivered to the Celery worker.
    """
    job = create_job(
        user=user,
        project=project,
        job_type=JOB_TYPE,
        metadata={"character_id": character_set.id},
    )
    execute_job.delay(job.id)
    return job


def _load_character(job):
    character_id = (job.metadata or {}).get("character_id")
    if not character_id:
        raise ValueError("character_id missing from job metadata")
    character_set = Character.objects.filter(id=character_id, project=job.project).first()
    if not character_set:
        raise ValueError(f"character set #{character_id} not found for job {job.id}")
    return character_set


def _existing_ids(character_set):
    """Return [(stable_id, name)] for previously detected characters (G-5)."""
    existing = []
    for char in character_set.characters or []:
        if isinstance(char, dict) and char.get("id"):
            existing.append((char["id"], (char.get("name") or "").strip()))
    return existing


def _commit_detection(job, character_set, result):
    """Persist the detected characters and move Gate 3 generating -> review.

    The Gate 3 review entry gate (at least one fully-defined character) is
    enforced here so only a usable character set reaches `review`.
    """
    characters = result.get("characters") or []
    if not characters:
        raise ValueError("character detection produced no characters")

    character_set.characters = characters
    character_set.version += 1
    character_set.transition_to(Character.GateState.REVIEW)
    character_set.save(
        update_fields=["characters", "version", "gate_state", "updated_at"]
    )
    record_audit(
        job.owner,
        AuditAction.UPDATE.value,
        "character",
        character_set.id,
        "character_detection_ready_for_review",
    )


def run_character_detection(job):
    """Executor for job_type `character_detection`.

    Invoked by execute_job as handler(job). Returns a result dict stored on the
    job; updates job.cost/provider. Any failure propagates to execute_job which
    marks the job failed.
    """
    character_set = _load_character(job)
    if not character_set.script:
        raise ValueError("character set has no attached script artifact")
    result = engine.detect_characters(
        character_set.script,
        existing_ids=_existing_ids(character_set),
    )
    _commit_detection(job, character_set, result)

    job.cost = result.get("cost", 0)
    job.provider = "openai"
    job.progress = 1.0
    job.save(update_fields=["cost", "provider", "progress", "updated_at"])

    return {
        "character_id": character_set.id,
        "gate_state": character_set.gate_state,
        "character_count": len(character_set.characters),
        "version": character_set.version,
    }


register_executor(JOB_TYPE, run_character_detection)
