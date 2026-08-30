# -*- coding: utf-8 -*-
"""Engine tests for scene media (per-scene visual/voice/music/subtitle)."""
import pytest

from apps.scene_media import engine
from apps.scene_media.models import SceneMedia
from apps.scene_media.providers.fake import FakeSceneMediaProvider

from .helpers import approved_scene_builder, make_project


@pytest.mark.django_db
class TestBuildMediaPayloads:
    def test_payloads_cover_all_four_types_per_scene(self, make_user):
        user = make_user(username="engine_payloads")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        payloads = engine.build_media_payloads(builder)
        assert len(payloads) == 2 * 4  # 2 scenes x 4 media types
        types = {p["media_type"] for p in payloads}
        assert types == {
            SceneMedia.MediaType.VISUAL,
            SceneMedia.MediaType.VOICE,
            SceneMedia.MediaType.MUSIC,
            SceneMedia.MediaType.SUBTITLE,
        }

    def test_stable_scene_ids_and_order_preserved(self, make_user):
        user = make_user(username="engine_order")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        scenes = builder.scenes
        seen_orders = [(s["id"], s["order"]) for s in scenes]
        assert ("s1", 1) in seen_orders
        assert ("s2", 2) in seen_orders
        # media payloads carry the same stable id/order as the package
        ids = {p["scene_id"] for p in engine.build_media_payloads(builder)}
        assert ids == {"s1", "s2"}

    def test_subset_request_only_yields_requested_type(self, make_user):
        user = make_user(username="engine_subset")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        payloads = engine.build_media_payloads(builder, media_types=["voice"])
        assert len(payloads) == 2
        assert all(p["media_type"] == SceneMedia.MediaType.VOICE for p in payloads)

    def test_unsupported_types_filtered_out(self, make_user):
        user = make_user(username="engine_filter")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        payloads = engine.build_media_payloads(
            builder, media_types=["voice", "banana"]
        )
        assert all(p["media_type"] == "voice" for p in payloads)

    def test_voice_and_music_defaults(self, make_user):
        user = make_user(username="engine_defaults")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        voice = next(
            p for p in engine.build_media_payloads(builder, ["voice"])
        )
        assert voice["voice"]["voice_id"] == "voice_default"
        music = next(
            p for p in engine.build_media_payloads(builder, ["music"])
        )
        assert music["music"]["mood"] == "neutral"


@pytest.mark.django_db
class TestGenerateSceneMedia:
    def test_fake_provider_produces_deterministic_assets(self, make_user):
        user = make_user(username="engine_gen")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        provider = FakeSceneMediaProvider()
        result = engine.generate_scene_media(provider, builder)
        assert result["count"] == 8
        assert result["media"][0]["scene_id"] == "s1"
        assert all(m["asset_ref"].startswith("mock://") for m in result["media"])
        # deterministic: same input -> same output
        second = engine.generate_scene_media(provider, builder)
        assert [m["asset_ref"] for m in second["media"]] == [
            m["asset_ref"] for m in result["media"]
        ]

    def test_generated_media_keeps_stable_ids_and_order(self, make_user):
        user = make_user(username="engine_identity")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.generate_scene_media(
            FakeSceneMediaProvider(), builder, media_types=["voice"]
        )
        assert [m["scene_id"] for m in result["media"]] == ["s1", "s2"]
        assert [m["scene_order"] for m in result["media"]] == [1, 2]
        assert all(m["characters"] for m in result["media"])  # G-5 stable ids

    def test_voice_media_includes_narration_and_duration(self, make_user):
        user = make_user(username="engine_voice")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.generate_scene_media(
            FakeSceneMediaProvider(), builder, media_types=["voice"]
        )
        voice = result["media"][0]
        assert voice["narration"]
        assert voice["duration_seconds"] >= 0
        assert voice["voice"]["voice_id"] == "voice_default"

    def test_music_media_includes_mood(self, make_user):
        user = make_user(username="engine_music")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.generate_scene_media(
            FakeSceneMediaProvider(), builder, media_types=["music"]
        )
        assert all(m["music"]["track"] for m in result["media"])

    def test_subtitle_media_includes_caption_lines(self, make_user):
        user = make_user(username="engine_subs")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        result = engine.generate_scene_media(
            FakeSceneMediaProvider(), builder, media_types=["subtitle"]
        )
        assert all("caption" in m and "format" in m["caption"] for m in result["media"])
