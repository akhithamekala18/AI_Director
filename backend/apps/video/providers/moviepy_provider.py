# -*- coding: utf-8 -*-
"""Real video provider using MoviePy + FFmpeg (DG-9 decision)."""
import logging
import os
import tempfile
import uuid

from apps.core import storage

logger = logging.getLogger("apps.video")

PLATFORM_CONFIG = {
    "YouTube": {"width": 1920, "height": 1080, "fps": 30, "aspect_ratio": "16:9", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
    "YouTube Shorts": {"width": 1080, "height": 1920, "fps": 30, "aspect_ratio": "9:16", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
    "TikTok": {"width": 1080, "height": 1920, "fps": 30, "aspect_ratio": "9:16", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
    "Instagram Reels": {"width": 1080, "height": 1920, "fps": 30, "aspect_ratio": "9:16", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
    "Instagram Feed": {"width": 1080, "height": 1080, "fps": 30, "aspect_ratio": "1:1", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
    "Twitter": {"width": 1920, "height": 1080, "fps": 30, "aspect_ratio": "16:9", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
    "LinkedIn": {"width": 1920, "height": 1080, "fps": 30, "aspect_ratio": "16:9", "codec": "libx264", "audio_codec": "aac", "container": "mp4"},
}

DEFAULT_CONFIG = PLATFORM_CONFIG["YouTube"]


def _get_config(platform_target):
    return PLATFORM_CONFIG.get(platform_target, DEFAULT_CONFIG)


def _create_scene_clip(scene, config, tmpdir):
    from moviepy import ColorClip, CompositeVideoClip, TextClip, AudioFileClip, ImageClip

    duration = scene.get("duration_seconds", 5)
    if duration <= 0:
        duration = 5

    visual_asset_ref = scene.get("visual_asset_ref", "")
    audio_asset_ref = scene.get("audio_asset_ref", "")

    clip = None

    if visual_asset_ref:
        try:
            visual_path = storage.get_path(visual_asset_ref)
            if os.path.isfile(visual_path):
                ext = os.path.splitext(visual_path)[1].lower()
                if ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
                    from moviepy import VideoFileClip
                    clip = VideoFileClip(visual_path).subclipped(0, duration)
                elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"):
                    clip = ImageClip(visual_path).with_duration(duration)
        except Exception as e:
            logger.warning("Failed to load visual asset %s: %s", visual_asset_ref, e)

    if clip is None:
        clip = ColorClip(size=(config["width"], config["height"]), color=(30, 30, 60), duration=duration)

    clip = clip.resized((config["width"], config["height"]))

    narration = scene.get("narration", "")
    if narration:
        try:
            txt_clip = TextClip(text=narration[:100], font_size=32, color="white", bg_color="black", size=(config["width"] - 100, None), method="caption", duration=duration).with_position(("center", "bottom"))
            clip = CompositeVideoClip([clip, txt_clip])
        except Exception:
            pass

    if audio_asset_ref:
        try:
            audio_path = storage.get_path(audio_asset_ref)
            if os.path.isfile(audio_path):
                audio = AudioFileClip(audio_path)
                if audio.duration > duration:
                    audio = audio.subclipped(0, duration)
                clip = clip.with_audio(audio)
        except Exception as e:
            logger.warning("Failed to load audio asset %s: %s", audio_asset_ref, e)

    return clip.with_duration(duration)


class MoviePyVideoProvider:
    """Real video provider using MoviePy + FFmpeg."""

    def composite(self, scenes, platform_target="YouTube"):
        if not scenes:
            raise ValueError("No scenes to composite")

        config = _get_config(platform_target)

        with tempfile.TemporaryDirectory(prefix="video_render_") as tmpdir:
            clips = []
            total_duration = 0

            for i, scene in enumerate(scenes):
                try:
                    clip = _create_scene_clip(scene, config, tmpdir)
                    if clip is not None:
                        clips.append(clip)
                        total_duration += clip.duration
                except Exception as e:
                    logger.error("Failed to create clip for scene %d: %s", i, e)
                    continue

            if not clips:
                raise RuntimeError("No scenes could be rendered into clips")

            from moviepy import concatenate_videoclips
            final = concatenate_videoclips(clips, method="compose")

            output_filename = f"video_{uuid.uuid4().hex[:12]}.{config['container']}"
            output_relative = f"videos/{output_filename}"
            output_path = storage.get_path(output_relative)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            final.write_videofile(output_path, fps=config["fps"], codec=config["codec"], audio_codec=config["audio_codec"], logger=None, temp_audiofile=os.path.join(tmpdir, "temp_audio.m4a"), remove_temp=True)

            for clip in clips:
                try:
                    clip.close()
                except Exception:
                    pass
            final.close()

            if not os.path.isfile(output_path):
                raise RuntimeError(f"Video file not created: {output_path}")

            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise RuntimeError(f"Video file is empty: {output_path}")

            with open(output_path, "rb") as f:
                saved_path = storage.save(f.read(), output_relative)

            return {
                "asset_ref": saved_path,
                "duration_seconds": int(total_duration),
                "provider": "moviepy",
                "provider_metadata": {
                    "renderer": "moviepy+ffmpeg",
                    "platform": platform_target,
                    "width": config["width"],
                    "height": config["height"],
                    "fps": config["fps"],
                    "codec": config["codec"],
                    "container": config["container"],
                    "scenes_composited": len(clips),
                    "file_size_bytes": file_size,
                    "aspect_ratio": config["aspect_ratio"],
                },
            }
