# -*- coding: utf-8 -*-
"""Research generation executor (Phase 2B, R5+R2).

Integrates research generation with the Phase 2A AsyncJob substrate: a
`research_generation` executor is registered via `register_executor()` so that
`execute_job` drives the job through pending -> running -> completed/failed
while the executor produces the Research artifact and moves Gate 1 from
`generating` to `review`.

Generation uses only the provider-agnostic engine (apps.research.engine), so no
live API credentials are required to exercise the flow (real provider execution
is NOT AVAILABLE here; runtime verification uses a fake adapter).
"""
from django.utils import timezone

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.services import create_job
from apps.ai_orchestration.tasks import execute_job, register_executor
from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from . import engine
from .models import Research, ResearchGap, ResearchSource

JOB_TYPE = AsyncJob.JobType.RESEARCH_GENERATION


def enqueue_research_job(user, project, research, regenerate=False):
    """Create and dispatch a research_generation AsyncJob for a Research row.

    Returns the created AsyncJob. In eager (test) mode the task executes
    synchronously; in production it is delivered to the Celery worker.
    """
    job = create_job(
        user=user,
        project=project,
        job_type=JOB_TYPE,
        metadata={
            "research_id": research.id,
            "regenerate": bool(regenerate),
        },
    )
    execute_job.delay(job.id)
    return job


def _load_research(job):
    research_id = (job.metadata or {}).get("research_id")
    if not research_id:
        raise ValueError("research_id missing from job metadata")
    research = Research.objects.filter(id=research_id, project=job.project).first()
    if not research:
        raise ValueError(f"research #{research_id} not found for job {job.id}")
    return research


def _commit_generation(job, research, result):
    """Persist the gathered artifact and move Gate 1 generating -> review."""
    summary = result["summary"]
    sources = result["sources"]
    gaps = result["gaps"]

    if not summary:
        raise ValueError("research generation produced an empty summary")
    if not sources:
        raise ValueError("research generation produced no cited sources")

    research.sources.all().delete()
    research.gaps.all().delete()

    for src in sources:
        ResearchSource.objects.create(
            research=research,
            url=src["url"],
            title=src["title"],
            snippet=src["snippet"],
            credibility_score=src["credibility_score"],
            accessed_at=timezone.now(),
        )

    for gap in gaps:
        ResearchGap.objects.create(
            research=research,
            gap_type=gap["gap_type"],
            description=gap["description"],
            source_a=gap["source_a"],
            source_b=gap["source_b"],
        )

    research.summary = summary
    research.raw_output = result.get("raw_output", {})
    research.version += 1
    research.transition_to(Research.GateState.REVIEW)
    research.save(
        update_fields=["summary", "raw_output", "version", "gate_state", "updated_at"]
    )
    record_audit(
        job.owner,
        AuditAction.UPDATE.value,
        "research",
        research.id,
        "research_ready_for_review",
    )


def run_research_generation(job):
    """Executor for job_type `research_generation`.

    Invoked by execute_job as handler(job). Returns a result dict stored on the
    job; updates job.cost/provider. Any failure propagates to execute_job which
    marks the job failed.
    """
    research = _load_research(job)
    result = engine.gather_research(job.project)
    _commit_generation(job, research, result)

    job.cost = result.get("cost", 0)
    job.provider = "openai"
    job.progress = 1.0
    job.save(update_fields=["cost", "provider", "progress", "updated_at"])

    return {
        "research_id": research.id,
        "gate_state": research.gate_state,
        "summary_length": len(research.summary),
        "source_count": research.sources.count(),
        "gap_count": research.gaps.count(),
    }


register_executor(JOB_TYPE, run_research_generation)
