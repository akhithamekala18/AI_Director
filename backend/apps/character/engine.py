# -*- coding: utf-8 -*-
"""Character detection engine (Phase 2D, Task 23 / Overview §20.1.4).

Consumes an approved Script (Gate 2) and produces the structured character
list: every on-screen character with their demographics (age, gender),
appearance (face shape, hair style, hair color, eyes, skin tone), clothing
(outfit, colors, style), accessories (glasses, jewelry, props), and an
illustrative style. Each character is assigned a stable ``id`` that is
persisted to the CharacterLibrary for cross-project reuse (G-5).

The engine depends only on the provider-agnostic AIProviderAdapter abstraction
(§24.3) obtained through the Phase 2A ProviderRegistry. It never reaches into a
concrete provider, so it is fully testable with a fake adapter and does not
require live API credentials.

Real provider execution is NOT AVAILABLE in this environment (no real
credentials); all runtime verification uses a deterministic fake provider.
"""
import json
from decimal import Decimal
from uuid import uuid4

from apps.ai_orchestration.services import get_provider

# Declarative schema hint sent to structured-output providers.
CHARACTER_SCHEMA = {
    "type": "object",
    "properties": {
        "characters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "string"},
                    "gender": {"type": "string"},
                    "appearance": {"type": "object"},
                    "clothing": {"type": "object"},
                    "accessories": {"type": "array", "items": {"type": "string"}},
                    "style": {"type": "object"},
                },
            },
        }
    },
}

# Sub-keys the parser normalizes inside each structured attribute group.
APPEARANCE_KEYS = (
    "face_shape",
    "hair_style",
    "hair_color",
    "eyes",
    "skin_tone",
)
CLOTHING_KEYS = ("outfit", "colors", "style")
STYLE_KEYS = ("illustrative_style", "realism", "palette")


def build_prompt(script):
    """Build the character-detection prompt from the approved script package."""
    body = (script.script or "").strip()
    narration = (script.narration or "").strip()
    scenes = json.dumps(script.scenes or [], ensure_ascii=False)
    return (
        "From the approved video script below, identify every on-screen "
        "character and define their visual attributes. Return JSON with exactly "
        "one key \"characters\" containing a list of character objects. Do not "
        "invent characters that the script does not describe.\n\n"
        "Script body:\n"
        f"{body}\n\n"
        "Narration:\n"
        f"{narration}\n\n"
        "Scenes (visual notes):\n"
        f"{scenes}\n\n"
        "For each character provide:\n"
        "- name: the character's name or label.\n"
        "- age: a short age descriptor (e.g. \"30s\").\n"
        "- gender: the character's gender descriptor.\n"
        "- appearance: object with face_shape, hair_style, hair_color, eyes, "
        "skin_tone.\n"
        "- clothing: object with outfit, colors (list), style.\n"
        "- accessories: list of items such as glasses, jewelry, props.\n"
        "- style: object with illustrative_style, realism, palette (list).\n"
        "Every character must include a non-empty name."
    )


def _ensure_stable_id(char, existing_ids):
    """Assign a persistent stable id, reusing a prior id when the name matches."""
    assignable = None
    for cid, cname in existing_ids:
        if cname == (char.get("name") or "").strip():
            assignable = cid
            break
    if assignable:
        return assignable
    candidate = f"char_{uuid4().hex[:12]}"
    while candidate in {cid for cid, _ in existing_ids}:
        candidate = f"char_{uuid4().hex[:12]}"
    return candidate


def parse_character_output(content, existing_ids=()):
    """Normalise raw provider `content` into a list of character dicts.

    Accepts a dict or a JSON string. Each character is validated/normalised to a
    stable shape with a guaranteed ``id`` so Gate 3 approval can rely on the
    stored attributes (G-5). existing_ids is a list of (stable_id, name) tuples
    so re-detection preserves identity for unchanged characters.
    """
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            content = {}
    content = content or {}
    raw_chars = content.get("characters") or []
    if not isinstance(raw_chars, list):
        raw_chars = []

    characters = []
    for raw in raw_chars:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        existing_ids = list(existing_ids)
        stable_id = _ensure_stable_id(raw, existing_ids)
        characters.append(
            {
                "id": stable_id,
                "name": name,
                "age": str(raw.get("age") or "").strip(),
                "gender": str(raw.get("gender") or "").strip(),
                "appearance": _normalize_group(raw.get("appearance"), APPEARANCE_KEYS),
                "clothing": _normalize_group(raw.get("clothing"), CLOTHING_KEYS),
                "accessories": _normalize_group(raw.get("accessories"), (), as_list=True),
                "style": _normalize_group(raw.get("style"), STYLE_KEYS),
            }
        )
    return characters


def _normalize_group(value, keys, as_list=False):
    """Coerce an attribute group to a stable dict (or list) shape."""
    value = value or {}
    if as_list:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, dict):
        value = {}
    out = {}
    for key in keys:
        item = value.get(key)
        if isinstance(item, list):
            out[key] = [str(i).strip() for i in item if str(i).strip()]
        elif item is not None:
            out[key] = str(item).strip()
    return out


def detect_characters(script, provider=None, existing_ids=()):
    """Produce the full character list from an approved script.

    Returns {"characters": [...], "cost": Decimal}. Each character carries a
    stable ``id`` for the library (G-5 identity).
    """
    provider = provider or get_provider()
    prompt = build_prompt(script)
    config = {"temperature": 0.5, "max_tokens": 2000}
    response = provider.generate_structured(
        prompt, schema=CHARACTER_SCHEMA, config=config
    )
    parsed = parse_character_output(response.get("content", {}), existing_ids)
    cost = response.get("cost", Decimal("0"))
    return {"characters": parsed, "cost": cost}
