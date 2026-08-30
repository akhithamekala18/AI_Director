# -*- coding: utf-8 -*-
"""Script generation executor (Phase 2C, R5+R2, Development Plan Day 22).

Integrates script generation with the Phase 2A AsyncJob substrate: a
`script_generation` executor is registered via `register_executor()` so that
`execute_job` drives the job through pending -> running -> completed/failed while
the executor produces the script package and moves Gate 2 from `generating` to
`review`.

Generation uses only the provider-agnostic engine (apps.script.engine), so no
live API credentials are required to exercise the flow (real provider execution
is NOT AVAILABLE here; runtime verification uses a fake adapter).
"""
from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.services import create_job
from apps.ai_orchestration.tasks import execute_job, register_executor
from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from . import engine
from .models import Script

JOB_TYPE = AsyncJob.JobType.SCRIPT_GENERATION


def enqueue_script_job(user, project, script):
    """Create and dispatch a script_generation AsyncJob for a Script row.

    Returns the created AsyncJob. In eager (test) mode the task executes
    synchronously; in production it is delivered to the Celery worker.
    """
    job = create_job(
        user=user,
        project=project,
        job_type=JOB_TYPE,
        metadata={"script_id": script.id},
    )
    execute_job.delay(job.id)
    return job


def _load_script(job):
    script_id = (job.metadata or {}).get("script_id")
    if not script_id:
        raise ValueError("script_id missing from job metadata")
    script = Script.objects.filter(id=script_id, project=job.project).first()
    if not script:
        raise ValueError(f"script #{script_id} not found for job {job.id}")
    return script


def _commit_generation(job, script, result):
    """Persist the gathered script package and move Gate 2 generating -> review.

    The G-2 review entry gate (title, script and narration non-empty) is
    enforced here so only a usable script package reaches `review`.
    """
    title = (result.get("title") or "").strip()
    script_body = (result.get("script") or "").strip()
    narration = (result.get("narration") or "").strip()

    if not title:
        raise ValueError("script generation produced an empty title")
    if not script_body:
        raise ValueError("script generation produced an empty script body")
    if not narration:
        raise ValueError("script generation produced empty narration")

    script.title = title
    script.outline = (result.get("outline") or "").strip()
    script.script = script_body
    script.narration = narration
    script.scenes = result.get("scenes") or []
    script.captions = result.get("captions") or []
    script.hashtags = result.get("hashtags") or []
    script.version += 1
    script.transition_to(Script.GateState.REVIEW)
    script.save(
        update_fields=[
            "title",
            "outline",
            "script",
            "narration",
            "scenes",
            "captions",
            "hashtags",
            "version",
            "gate_state",
            "updated_at",
        ]
    )
    record_audit(
        job.owner,
        AuditAction.UPDATE.value,
        "script",
        script.id,
        "script_ready_for_review",
    )


def run_script_generation(job):
    """Executor for job_type `script_generation`.

    Invoked by execute_job as handler(job). Returns a result dict stored on the
    job; updates job.cost/provider. Any failure propagates to execute_job which
    marks the job failed.
    """
    script = _load_script(job)
    if not script.research:
        raise ValueError("script has no attached research artifact")
    result = engine.gather_script(script.research)
    _commit_generation(job, script, result)

    job.cost = result.get("cost", 0)
    job.provider = "openai"
    job.progress = 1.0
    job.save(update_fields=["cost", "provider", "progress", "updated_at"])

    return {
        "script_id": script.id,
        "gate_state": script.gate_state,
        "title_length": len(script.title),
        "script_length": len(script.script),
        "scene_count": len(script.scenes),
    }


register_executor(JOB_TYPE, run_script_generation)
