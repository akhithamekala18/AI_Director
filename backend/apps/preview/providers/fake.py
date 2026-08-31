# -*- coding: utf-8 -*-
"""Fake preview provider for deterministic testing (Task 37).

Produces deterministic preview metadata without external API calls.
"""
import uuid


class FakePreviewProvider:
    """Deterministic fake preview renderer for tests."""

    PROVIDER_NAME = "fake_preview"

    def render_preview(self, video_asset, platform_target):
        """Render a platform-accurate preview from a video asset.

        Returns dict with:
          asset_ref: unique reference
          provider: provider name
          provider_metadata: rendering metadata
          duration_seconds: preview duration
        """
        aspect_map = {
            "YouTube": "16:9",
            "TikTok": "9:16",
            "Instagram Reels": "9:16",
            "Instagram Feed": "1:1",
            "Twitter": "16:9",
            "LinkedIn": "16:9",
        }
        aspect = aspect_map.get(platform_target, "16:9")
        width, height = (1920, 1080) if aspect == "16:9" else (1080, 1920)
        if aspect == "1:1":
            width, height = 1080, 1080

        return {
            "asset_ref": f"preview-{uuid.uuid4().hex[:12]}",
            "provider": self.PROVIDER_NAME,
            "provider_metadata": {
                "platform_target": platform_target,
                "aspect_ratio": aspect,
                "width": width,
                "height": height,
                "scene_count": getattr(video_asset, "scene_count", 0),
                "render_mode": "platform_accurate",
            },
            "duration_seconds": getattr(video_asset, "duration_seconds", 0),
            "width": width,
            "height": height,
        }
