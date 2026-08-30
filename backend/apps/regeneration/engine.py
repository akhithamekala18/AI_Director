# -*- coding: utf-8 -*-
"""Regeneration engine (Phase 2G, Task 26 / Overview §26, §20.2.2).

Deterministic, provider-independent helpers that decide WHAT a regeneration run
will regenerate from an APPROVED Scene Builder package (Gate 4) and the existing
Task 25 media, and validate scope (G-4: single scene by default; full only when
explicitly requested).

The engine never regenerates anything itself; it only resolves the target scene
and payloads. The executor performs the actual provider calls.
"""
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.scene_media.engine import build_media_payloads, requested_media_types

_MISSING_SCENE_MSG = "scene does not exist in the approved scene package"
_EMPTY_PACKAGE_MSG = "approved scene package has no scenes"


def resolve_scope(scene_id, full):
    """Resolve the regeneration target scope.

    Returns ("scene", scene_id) when scoped to a single scene, or ("full", None)
    for full regeneration. Enforces G-4: full regeneration is only allowed when
    explicitly requested (``full=True``); a missing scoped scene_id is invalid.
    """
    if full:
        return "full", None
    if not scene_id:
        raise DjangoValidationError("scene_id is required unless full regeneration is requested")
    return "scene", scene_id


def validate_scene_exists(builder, scene_id):
    """Ensure ``scene_id`` is a stable scene id in the approved package."""
    scenes = builder.scenes or []
    if not scenes:
        raise DjangoValidationError(_EMPTY_PACKAGE_MSG)
    for scene in scenes:
        if scene.get("id") == scene_id:
            return scene
    raise DjangoValidationError(_MISSING_SCENE_MSG)


def resolve_targets(builder, scene_id, full, media_types=None):
    """Return the scene(s) and media types this run will regenerate.

    Returns a dict: {scopes: ["scene", ...], media_types: [...]}. For scoped
    regeneration the single target scene is validated to exist; for full it is
    all scenes. This defines the deterministic blast radius.
    """
    scenes = builder.scenes or []
    if not scenes:
        raise DjangoValidationError(_EMPTY_PACKAGE_MSG)

    scope, resolved_scene_id = resolve_scope(scene_id, full)
    media_types = media_types or []

    if scope == "scene":
        scene = validate_scene_exists(builder, resolved_scene_id)
        targets = [scene]
    else:
        targets = list(scenes)

    # Normalise requested media types; empty means "all media types".
    types = requested_media_types(media_types)
    return {"scopes": targets, "media_types": types, "scope": scope}


def build_regeneration_payloads(builder, targets, media_types):
    """Build per-scene regeneration payloads for the targeted scenes only.

    Reuses the frozen scene_media engine's payload builder for each target
    scene, restricted to the target media types. This guarantees the payloads
    are identical in shape to the Task 25 generation payloads and stay scoped
    to the targeted scenes (deterministic blast radius).
    """
    payloads = []
    for scene in targets:
        for payload in build_media_payloads_for_scene(builder, scene, media_types):
            payloads.append(payload)
    return payloads


def build_media_payloads_for_scene(builder, scene, media_types):
    """Build payloads for a single target scene for the given media types."""
    payloads = build_media_payloads(builder, media_types)
    return [p for p in payloads if p["scene_id"] == scene.get("id")]
