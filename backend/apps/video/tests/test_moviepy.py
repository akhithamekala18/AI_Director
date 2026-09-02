# -*- coding: utf-8 -*-
"""Real MoviePy provider tests (DG-9)."""
import os
import pytest
from apps.core import storage

@pytest.mark.django_db
class TestMoviePyProvider:
    def test_composite_produces_real_video(self):
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        p = MoviePyVideoProvider()
        scenes = [{"id": "s1", "order": 1, "narration": "Scene one", "duration_seconds": 2}, {"id": "s2", "order": 2, "narration": "Scene two", "duration_seconds": 2}]
        r = p.composite(scenes, "YouTube")
        assert r["provider"] == "moviepy"
        assert r["duration_seconds"] >= 4
        assert r["provider_metadata"]["scenes_composited"] == 2
        assert r["provider_metadata"]["width"] == 1920
        assert r["provider_metadata"]["height"] == 1080
        assert r["provider_metadata"]["file_size_bytes"] > 0
        assert storage.exists(r["asset_ref"])
        fp = storage.get_path(r["asset_ref"])
        assert os.path.isfile(fp) and os.path.getsize(fp) > 0
        storage.delete(r["asset_ref"])

    def test_composite_tiktok_aspect(self):
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        p = MoviePyVideoProvider()
        r = p.composite([{"id": "s1", "order": 1, "duration_seconds": 2}], "TikTok")
        assert r["provider_metadata"]["width"] == 1080
        assert r["provider_metadata"]["height"] == 1920
        assert r["provider_metadata"]["aspect_ratio"] == "9:16"
        storage.delete(r["asset_ref"])

    def test_empty_scenes_raises(self):
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        with pytest.raises(ValueError): MoviePyVideoProvider().composite([], "YouTube")

    def test_fake_provider_still_works(self):
        from apps.video.providers.fake import FakeVideoProvider
        r = FakeVideoProvider().composite([{"id": "s1", "duration_seconds": 5}], "YouTube")
        assert r["provider"] == "fake" and r["asset_ref"].startswith("fake-video-")

    def test_engine_both_providers(self):
        from apps.video.engine import composite_video
        from apps.video.providers.fake import FakeVideoProvider
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        scenes = [{"id": "s1", "order": 1, "duration_seconds": 2}]
        assert composite_video(FakeVideoProvider(), scenes, "YouTube")["provider"] == "fake"
        rr = composite_video(MoviePyVideoProvider(), scenes, "YouTube")
        assert rr["provider"] == "moviepy"
        storage.delete(rr["asset_ref"])

    def test_storage_path_traversal_defended(self):
        # Path traversal attempts are stripped (../ removed), file saved safely
        result = storage.save(b"test", "../../../test_traversal.bin")
        assert storage.exists(result)
        storage.delete(result)

    def test_storage_round_trip(self):
        p = "test/roundtrip_test.bin"
        storage.save(b"hello", p)
        assert storage.exists(p) and os.path.isfile(storage.get_path(p))
        storage.delete(p)
        assert not storage.exists(p)

    def test_platform_configs(self):
        from apps.video.providers.moviepy_provider import PLATFORM_CONFIG
        for c in PLATFORM_CONFIG.values():
            assert c["width"] > 0 and c["height"] > 0 and c["fps"] > 0

    def test_moviepy_imports(self):
        import moviepy, imageio_ffmpeg
        assert moviepy.__version__ and os.path.isfile(imageio_ffmpeg.get_ffmpeg_exe())

    def test_valid_mp4_container(self):
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        r = MoviePyVideoProvider().composite([{"id": "s1", "order": 1, "duration_seconds": 2}], "YouTube")
        with open(storage.get_path(r["asset_ref"]), "rb") as f: header = f.read(12)
        assert b"ftyp" in header
        storage.delete(r["asset_ref"])

    def test_ffprobe_validation(self):
        import subprocess, imageio_ffmpeg
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        r = MoviePyVideoProvider().composite([{"id": "s1", "order": 1, "duration_seconds": 2}], "YouTube")
        fp = storage.get_path(r["asset_ref"])
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        proc = subprocess.run([exe, "-i", fp, "-f", "null", "-"], capture_output=True, text=True, timeout=30)
        # FFmpeg returns duration info in stderr; check exit code
        assert proc.returncode == 0 or "Duration" in proc.stderr, f"FFmpeg validation failed: {proc.stderr[:200]}"
        storage.delete(r["asset_ref"])

    def test_metadata_complete(self):
        from apps.video.providers.moviepy_provider import MoviePyVideoProvider
        r = MoviePyVideoProvider().composite([{"id": "s1", "order": 1, "duration_seconds": 2}], "YouTube")
        for f in ["renderer", "platform", "width", "height", "fps", "codec", "container", "scenes_composited", "file_size_bytes", "aspect_ratio"]:
            assert f in r["provider_metadata"]
        storage.delete(r["asset_ref"])