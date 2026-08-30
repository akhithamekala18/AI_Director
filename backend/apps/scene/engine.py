# -*- coding: utf-8 -*-
"""Scene Builder engine (Phase 2E, Task 24 / Overview §20.1.6).

Maps the approved Script's scene decomposition (Gate 2) into a structured scene
package for Gate 4 approval. It is fully deterministic — it does not call any AI
provider, it only re-assembles and enriches already approved content:

  * scene order comes from the Script's scene list order;
  * narration / visual direction come from each Script scene's narration and
    visual_notes (with a top-level narration fallback);
  * assigned characters come from the approved Character set (Gate 3) and are
    stored by their stable library ``character_id`` (G-5 identity preservation);
  * pacing and transitions default deterministically and can be set per build.

Because no external provider is invoked, real provider runtime verification is
NOT APPLICABLE (and therefore NOT VERIFIED); the engine is exercised with the
sync build flow in tests.
"""
from uuid import uuid4

SCENE_KINDS = ("intro", "body", "outro")

DEFAULT_PACING = "normal"
DEFAULT_TRANSITION = "cut"
DEFAULT_DURATION = 8


def build_scene_package(
    script,
    characters,
    pacing=DEFAULT_PACING,
    transition=DEFAULT_TRANSITION,
    duration=DEFAULT_DURATION,
):
    """Map the approved Script scenes into a deterministic scene package.

    ``script.scenes`` is the authoritative scene decomposition produced by the
    Script Generator (Gate 2). ``characters`` is the approved Character set's
    ``characters`` list (Gate 3), each with a stable ``id``.

    Returns {"scenes": [...], "scene_count": <int>}. Every scene carries a
    stable ``id``, its ``order``, ``heading``, ``narration``, ``visual_direction``,
    assigned ``characters`` (stable ids), ``pacing``, ``transition``,
    ``duration_seconds``, and ``metadata``.
    """
    raw_scenes = script.scenes or []
    characters = [c for c in (characters or []) if isinstance(c, dict) and c.get("id")]
    top_narration = (script.narration or "").strip()

    scenes = []
    for index, raw in enumerate(raw_scenes, start=1):
        if not isinstance(raw, dict):
            continue
        heading = str(raw.get("heading") or "").strip() or f"Scene {index}"
        narration = str(raw.get("narration") or "").strip() or top_narration
        visual_direction = str(raw.get("visual_notes") or "").strip()
        scene_text = f"{heading} {narration} {visual_direction}"
        scenes.append(
            {
                "id": _stable_scene_id(raw, index),
                "order": index,
                "heading": heading,
                "narration": narration,
                "visual_direction": visual_direction,
                "characters": assign_characters(scene_text, characters),
                "pacing": pacing,
                "transition": transition,
                "duration_seconds": int(duration),
                "metadata": {"kind": scene_kind(index, len(raw_scenes))},
            }
        )

    return {"scenes": scenes, "scene_count": len(scenes)}


def _stable_scene_id(raw, index):
    """Reuse the Script scene id when present, else generate a stable one."""
    existing = str(raw.get("id") or "").strip()
    if existing:
        return existing
    return f"scene_{uuid4().hex[:12]}"


def assign_characters(scene_text, characters):
    """Deterministically map approved library characters to one scene.

    A character is assigned when its name appears (case-insensitive) in the
    scene's heading/narration/visual direction; if none match, the first
    library character is assigned so the scene always has a reference. Returns a
    list of stable character ids (G-5: reference by identity, never by value).
    """
    text = (scene_text or "").lower()
    matched = []
    for char in characters:
        name = str(char.get("name") or "").strip().lower()
        if name and name in text:
            matched.append(char["id"])
    if not matched and characters:
        matched = [characters[0]["id"]]
    return matched


def scene_kind(index, total):
    """Classify a scene position deterministically: intro / body / outro."""
    if total <= 1:
        return "body"
    if index == 1:
        return "intro"
    if index == total:
        return "outro"
    return "body"
