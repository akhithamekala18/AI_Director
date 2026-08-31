# -*- coding: utf-8 -*-
"""Fake thumbnail provider for deterministic testing (Task 36)."""


class FakeThumbnailProvider:
    """Deterministic fake provider that simulates thumbnail generation.

    Returns predictable output for testing without requiring real image
    processing capabilities.
    """

    def generate(self, scenes, title_text="", platform_target="YouTube"):
        """Simulate generating a thumbnail from scene visuals.

        Args:
            scenes: List of scene data dicts from the approved Scene Builder.
            title_text: Title text to overlay on the thumbnail.
            platform_target: Target platform for dimensions.

        Returns:
            dict with asset_ref, variations, and metadata.
        """
        variations = [
            f"fake-thumb-{i}-{platform_target.lower()}"
            for i in range(1, 4)
        ]
        return {
            "asset_ref": variations[0],
            "variations": variations,
            "provider": "fake",
            "provider_metadata": {
                "scene_count": len(scenes),
                "platform": platform_target,
                "title_text": title_text,
            },
        }
