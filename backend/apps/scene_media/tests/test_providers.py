# -*- coding: utf-8 -*-
"""Provider abstraction tests: deterministic fake, no secret leakage."""

from apps.scene_media.providers.base import SceneMediaProviderError
from apps.scene_media.providers.fake import FakeSceneMediaProvider


class TestFakeSceneMediaProvider:
    def test_name(self):
        assert FakeSceneMediaProvider.name == "fake"

    def test_visual_deterministic(self):
        provider = FakeSceneMediaProvider()
        payload = {
            "scene_id": "s1",
            "media_type": "visual",
            "visual_direction": "volcano wide shot",
        }
        a = provider.generate_visual(payload)
        b = provider.generate_visual(payload)
        assert a["asset_ref"] == b["asset_ref"]
        assert a["asset_ref"].startswith("mock://visual/s1")
        assert a["provider_metadata"]["mock"] is True

    def test_voice_carries_voice_id_and_word_count(self):
        payload = {
            "scene_id": "s1",
            "narration": "What causes a volcano to erupt?",
            "voice": {"voice_id": "maya"},
        }
        result = FakeSceneMediaProvider().generate_voice(payload)
        assert result["voice"]["voice_id"] == "maya"
        assert result["voice"]["words"] == 6

    def test_music_carries_mood(self):
        payload = {"scene_id": "s1", "music": {"mood": "dramatic"}}
        result = FakeSceneMediaProvider().generate_music(payload)
        assert result["music"]["mood"] == "dramatic"
        assert result["music"]["track"] == "track_dramatic"

    def test_subtitle_carries_caption_lines(self):
        payload = {"scene_id": "s1", "narration": "Line one|Line two"}
        result = FakeSceneMediaProvider().generate_subtitle(payload)
        assert result["caption"]["lines"] == ["Line one", "Line two"]
        assert result["caption"]["format"] == "srt"

    def test_no_secret_keys_in_provider_metadata(self):
        provider = FakeSceneMediaProvider()
        for method, payload in [
            ("generate_visual", {"scene_id": "s1"}),
            ("generate_voice", {"scene_id": "s1", "narration": "hi"}),
            ("generate_music", {"scene_id": "s1"}),
            ("generate_subtitle", {"scene_id": "s1", "narration": "hi"}),
        ]:
            result = getattr(provider, method)(payload)
            meta = result.get("provider_metadata", {})
            joined = str(meta).lower()
            for needle in ("api", "secret", "key", "token", "password", "bearer"):
                assert needle not in joined


class TestErrors:
    def test_error_type_exists(self):
        err = SceneMediaProviderError("boom", retryable=False)
        assert err.retryable is False
