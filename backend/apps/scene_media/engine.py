# -*- coding: utf-8 -*-
"""Scene Media engine (Phase 2F, Task 25 / Overview §20.1.8–20.1.10).

Turns the *approved* Scene Builder package (Gate 4) into per-scene media
payloads for each requested media type — visual, voice, music, subtitle — and
drives them through a provider-agnostic abstraction. The engine itself never
calls a provider; it delegates to a ``SceneMediaProvider`` and returns the
structured per-scene assets.

Preservation guarantees (G-4, G-5):
  * scene_id and scene_order come directly from the approved package, so media
    stays tied to the correct scene and ordering is preserved;
  * character references continue by stable character identity (never recreated
    or silently replaced).

It is deterministic given the approved package and a deterministic provider, so
tests require no network or credentials.
"""
from .models import SceneMedia

ALL_MEDIA_TYPES = [SceneMedia.MediaType.VISUAL, SceneMedia.MediaType.VOICE, SceneMedia.MediaType.MUSIC, SceneMedia.MediaType.SUBTITLE]

# Default voice / music characteristics (doc §20.1.8 voice characteristics,
# §20.1.9 per-scene music mood). Applied to every scene unless overridden.
DEFAULT_VOICE = {"voice_id": "voice_default", "style": "natural"}
DEFAULT_MUSIC = {"mood": "neutral", "mixing": "background"}


def requested_media_types(media_types):
    """Normalise a media type request into the ordered allowed list."""
    if not media_types:
        return list(ALL_MEDIA_TYPES)
    allowed = {t for t in SceneMedia.MediaType.values}
    result = []
    for mt in media_types:
        if mt in allowed and mt not in result:
            result.append(mt)
    return result


def build_media_payloads(builder, media_types=None):
    """Build a deterministic per-scene media plan from the approved package.

    Returns a list of payload dicts, one per (scene x media type), each carrying
    the stable scene id/order, narration/visual direction, characters, pacing,
    transition, duration, and media-type-specific defaults. Never touches the
    approved package (it is read-only input).
    """
    scenes = builder.scenes or []
    types = requested_media_types(media_types)
    payloads = []
    for scene in scenes:
        for mt in types:
            payloads.append(
                {
                    "scene_id": scene.get("id", ""),
                    "scene_order": scene.get("order", 0),
                    "media_type": mt,
                    "heading": scene.get("heading", ""),
                    "narration": scene.get("narration", ""),
                    "visual_direction": scene.get("visual_direction", ""),
                    "characters": scene.get("characters", []),
                    "pacing": scene.get("pacing", "normal"),
                    "transition": scene.get("transition", "cut"),
                    "duration_seconds": scene.get("duration_seconds", 0),
                    "voice": dict(DEFAULT_VOICE),
                    "music": dict(DEFAULT_MUSIC),
                    "kind": (scene.get("metadata") or {}).get("kind", "body"),
                }
            )
    return payloads


def generate_scene_media(provider, builder, media_types=None):
    """Generate per-scene media through ``provider``.

    Returns {"media": [ {scene_id, scene_order, media_type, asset_ref,
    provider_metadata, voice, music, caption} ... ]} for each produced asset.
    """
    records = []
    for payload in build_media_payloads(builder, media_types):
        mt = payload["media_type"]
        if mt == SceneMedia.MediaType.VISUAL:
            result = provider.generate_visual(payload)
        elif mt == SceneMedia.MediaType.VOICE:
            result = provider.generate_voice(payload)
        elif mt == SceneMedia.MediaType.MUSIC:
            result = provider.generate_music(payload)
        elif mt == SceneMedia.MediaType.SUBTITLE:
            result = provider.generate_subtitle(payload)
        else:
            continue
        records.append(
            {
                "scene_id": payload["scene_id"],
                "scene_order": payload["scene_order"],
                "media_type": mt,
                "asset_ref": result.get("asset_ref", ""),
                "provider_metadata": result.get("provider_metadata", {}),
                "voice": result.get("voice") or payload.get("voice"),
                "music": result.get("music") or payload.get("music"),
                "caption": result.get("caption") or {},
                "duration_seconds": payload["duration_seconds"],
                "pacing": payload["pacing"],
                "transition": payload["transition"],
                "narration": payload["narration"],
                "characters": payload["characters"],
            }
        )
    return {"media": records, "count": len(records)}
