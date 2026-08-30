# -*- coding: utf-8 -*-
"""Research engine (R5, Development Plan Day 21 / Overview §20.1.2).

Accepts a topic; gathers information from a set of cited sources; produces a
cited summary, a source list, and gap/contradiction flags; and presents the
result for approval (Gate 1).

The engine depends only on the provider-agnostic AIProviderAdapter abstraction
(§24.3) obtained through the Phase 2A ProviderRegistry. It never reaches into a
concrete provider, so it is fully testable with a fake adapter and does not
require live API credentials.

Real provider execution is NOT AVAILABLE in this environment (no real
credentials); all runtime verification uses a deterministic fake provider.
"""
import json
from decimal import Decimal

from apps.ai_orchestration.services import get_provider

# Declarative schema hint sent to structured-output providers.
RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "snippet": {"type": "string"},
                    "credibility_score": {"type": "number"},
                },
            },
        },
        "gaps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["gap", "contradiction"]},
                    "description": {"type": "string"},
                    "source_a": {"type": "string"},
                    "source_b": {"type": "string"},
                },
            },
        },
    },
}


def build_prompt(project):
    """Build the research-gathering prompt for a project topic."""
    topic = (project.topic or "").strip()
    platform = project.platform_target or "general"
    return (
        "Research the following topic thoroughly for a short-form video.\n\n"
        f"Topic: {topic}\nPlatform target: {platform}\n\n"
        "Return JSON with:\n"
        "- summary: a factual, citation-backed summary (2-4 sentences).\n"
        "- sources: a list of 1+ trustworthy sources, each with url, title, "
        "snippet, and a credibility_score from 0.0 to 1.0.\n"
        "- gaps: a list of gaps or contradictions found across sources, each "
        "with type ('gap' or 'contradiction'), description, and optional "
        "source_a/source_b references.\n"
        "Every claim in the summary must be supportable by the listed sources. "
        "Do not fabricate sources."
    )


def parse_research_output(content):
    """Normalise raw provider `content` into {summary, sources, gaps}.

    Accepts a dict or a JSON string (providers may return either). Malformed
    entries are dropped so the engine degrades gracefully and the Gate 1
    generating -> review validation (summary non-empty, >=1 source) still
    applies afterwards.
    """
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            content = {}
    content = content or {}

    summary = str(content.get("summary") or "").strip()

    sources = []
    for raw in content.get("sources") or []:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        if not url:
            continue
        sources.append(
            {
                "url": url,
                "title": str(raw.get("title") or "").strip(),
                "snippet": str(raw.get("snippet") or "").strip(),
                "credibility_score": _as_float(raw.get("credibility_score")),
            }
        )

    gaps = []
    for raw in content.get("gaps") or []:
        if not isinstance(raw, dict):
            continue
        gap_type = str(raw.get("type") or "gap").strip().lower()
        if gap_type not in ("gap", "contradiction"):
            gap_type = "gap"
        gaps.append(
            {
                "gap_type": gap_type,
                "description": str(raw.get("description") or "").strip(),
                "source_a": str(raw.get("source_a") or "").strip(),
                "source_b": str(raw.get("source_b") or "").strip(),
            }
        )

    return {"summary": summary, "sources": sources, "gaps": gaps}


def gather_research(project, provider=None):
    """Run one research pass and return a structured result.

    Args:
        project: The Project being researched.
        provider: An AIProviderAdapter. Defaults to the configured provider via
            the Phase 2A ProviderRegistry.

    Returns:
        dict: {"summary", "sources", "gaps", "cost"}.
    """
    provider = provider or get_provider()
    prompt = build_prompt(project)
    config = {"temperature": 0.3, "max_tokens": 2048}
    response = provider.generate_structured(
        prompt, schema=RESEARCH_SCHEMA, config=config
    )
    content = response.get("content", {})
    parsed = parse_research_output(content)
    cost = response.get("cost", Decimal("0"))
    return {
        "summary": parsed["summary"],
        "sources": parsed["sources"],
        "gaps": parsed["gaps"],
        "cost": cost,
    }


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
