# -*- coding: utf-8 -*-
"""Fake video provider for deterministic testing (Task 36)."""


class FakeVideoProvider:
    """Deterministic fake provider that simulates video compositing.

    Returns predictable output for testing without requiring real media
    processing capabilities.
    """

    def composite(self, scenes, platform_target="YouTube"):
        """Simulate compositing scenes into a video.

        Args:
            scenes: List of scene data dicts from the approved Scene Builder.
            platform_target: Target platform for aspect ratio/format.

        Returns:
            dict with asset_ref, duration_seconds, and metadata.
        """
        total_duration = sum(s.get("duration_seconds", 5) for s in scenes)
        return {
            "asset_ref": f"fake-video-{len(scenes)}scenes-{platform_target.lower()}",
            "duration_seconds": total_duration or len(scenes) * 5,
            "provider": "fake",
            "provider_metadata": {
                "scenes_composited": len(scenes),
                "platform": platform_target,
            },
        }
