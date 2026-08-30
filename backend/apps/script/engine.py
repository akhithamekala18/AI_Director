# -*- coding: utf-8 -*-
"""Script generation engine (R5-style, Development Plan Day 22 / Overview
§20.1.3).

Consumes the approved Research artifact and produces the complete script
package: working title, outline, full script with narration, scene
decomposition, captions and on-screen text, and platform hashtags.

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
SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "outline": {"type": "string"},
        "script": {"type": "string"},
        "narration": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "heading": {"type": "string"},
                    "narration": {"type": "string"},
                    "visual_notes": {"type": "string"},
                },
            },
        },
        "captions": {"type": "array", "items": {"type": "string"}},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
}


def build_prompt(research):
    """Build the script-generation prompt from the approved research summary."""
    summary = (research.summary or "").strip()
    return (
        "Write a complete, production-ready short-form video script package "
        "based strictly on the approved research below. Do not introduce facts "
        "not supported by the research.\n\n"
        f"Approved research summary:\n{summary}\n\n"
        "Return JSON with exactly these keys:\n"
        "- title: a working title for the video.\n"
        "- outline: the episode structure.\n"
        "- script: the full spoken script.\n"
        "- narration: the voice-over narration text.\n"
        "- scenes: a list of scene objects, each with id, heading, narration, "
        "and visual_notes.\n"
        "- captions: a list of caption strings / on-screen text.\n"
        "- hashtags: a list of platform hashtags.\n"
        "Every field must be present and non-empty."
    )


def parse_script_output(content):
    """Normalise raw provider `content` into the script package dict.

    Accepts a dict or a JSON string. Missing/empty scalar fields are coerced to
    empty values so the Gate 2 generating -> review validation (title, script
    and narration non-empty) still applies afterwards.
    """
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            content = {}
    content = content or {}

    def _text(key):
        return str(content.get(key) or "").strip()

    scenes = []
    for raw in content.get("scenes") or []:
        if not isinstance(raw, dict):
            continue
        scenes.append(
            {
                "id": str(raw.get("id") or "").strip(),
                "heading": str(raw.get("heading") or "").strip(),
                "narration": str(raw.get("narration") or "").strip(),
                "visual_notes": str(raw.get("visual_notes") or "").strip(),
            }
        )

    captions = [
        str(c).strip() for c in (content.get("captions") or []) if str(c).strip()
    ]
    hashtags = [
        str(h).strip() for h in (content.get("hashtags") or []) if str(h).strip()
    ]

    return {
        "title": _text("title"),
        "outline": _text("outline"),
        "script": _text("script"),
        "narration": _text("narration"),
        "scenes": scenes,
        "captions": captions,
        "hashtags": hashtags,
        "cost": content.get("cost", 0),
    }


def gather_script(research, provider=None):
    """Produce one script package from approved research.

    Returns {"title", "outline", "script", "narration", "scenes", "captions",
    "hashtags", "cost"}.
    """
    provider = provider or get_provider()
    prompt = build_prompt(research)
    config = {"temperature": 0.6, "max_tokens": 3000}
    response = provider.generate_structured(
        prompt, schema=SCRIPT_SCHEMA, config=config
    )
    parsed = parse_script_output(response.get("content", {}))
    cost = response.get("cost", Decimal("0"))
    return {
        "title": parsed["title"],
        "outline": parsed["outline"],
        "script": parsed["script"],
        "narration": parsed["narration"],
        "scenes": parsed["scenes"],
        "captions": parsed["captions"],
        "hashtags": parsed["hashtags"],
        "cost": cost,
    }
