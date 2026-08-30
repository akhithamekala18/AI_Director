# -*- coding: utf-8 -*-
"""Deterministic fake scene media provider (Phase 2F, Task 25).

Used as the default (and test) provider so that generation is fully hermetic,
offline, repeatable, and free of any external API key or network dependency.
It never writes a real asset; it returns a deterministic ``asset_ref`` and a
small, opaque provider metadata dict derived solely from the scene payload.

This is the provider exercised by every test. Real external providers remain
pluggable behind the same interface but were NOT invoked in this environment
(see runtime verification report).
"""
from .base import SceneMediaProvider


def _stub_ref(media_type, scene_id):
    return f"mock://{media_type}/{scene_id}"


class FakeSceneMediaProvider(SceneMediaProvider):
    """Deterministic, offline provider used for tests and default runtime."""

    name = "fake"

    def generate_visual(self, payload):
        scene_id = payload["scene_id"]
        direction = payload.get("visual_direction") or payload.get("direction") or ""
        return {
            "asset_ref": _stub_ref("visual", scene_id),
            "provider_metadata": {
                "caption_digest": _digest(direction),
                "mock": True,
            },
        }

    def generate_voice(self, payload):
        scene_id = payload["scene_id"]
        narration = payload.get("narration") or ""
        voice_id = (payload.get("voice") or {}).get("voice_id") or "voice_default"
        return {
            "asset_ref": _stub_ref("voice", scene_id),
            "voice": {"voice_id": voice_id, "words": _words(narration)},
            "provider_metadata": {"mock": True},
        }

    def generate_music(self, payload):
        scene_id = payload["scene_id"]
        mood = (payload.get("music") or {}).get("mood") or "neutral"
        return {
            "asset_ref": _stub_ref("music", scene_id),
            "music": {"mood": mood, "track": f"track_{mood}"},
            "provider_metadata": {"mock": True},
        }

    def generate_subtitle(self, payload):
        scene_id = payload["scene_id"]
        narration = payload.get("narration") or ""
        return {
            "asset_ref": _stub_ref("subtitle", scene_id),
            "caption": {"lines": _lines(narration), "format": "srt"},
            "provider_metadata": {"mock": True},
        }


def _digest(text):
    return abs(hash(text or "")) % 10_000_000


def _words(text):
    return len([w for w in (text or "").split() if w.strip()])


def _lines(text):
    return [line for line in (text or "").split("|") if line.strip()]
