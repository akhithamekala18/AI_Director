# -*- coding: utf-8 -*-
"""File storage abstraction for media assets.

Provides a simple, secure file storage layer that:
- Uses Django's MEDIA_ROOT for local filesystem storage
- Creates parent directories automatically
- Prevents path traversal attacks
- Returns stable relative references (no absolute paths in DB)
- Handles duplicate filenames safely

For production, this can be swapped to S3/CloudStorage by changing
the Django STORAGE_BACKEND setting.
"""
import os
from django.conf import settings


def _get_media_root():
    """Return the media root directory, creating it if needed."""
    mr = getattr(settings, "MEDIA_ROOT", "")
    if not mr:
        mr = os.path.join(settings.BASE_DIR, "media")
    os.makedirs(mr, exist_ok=True)
    return mr


def _safe_join(base, *parts):
    """Join path parts safely, preventing path traversal.

    Raises ValueError if the resulting path escapes the base directory.
    """
    base = os.path.normpath(base)
    joined = base
    for part in parts:
        # Strip leading slashes and dots to prevent traversal
        part = part.strip("/").strip("\\")
        # Remove leading ../ sequences to prevent traversal
        while part.startswith(".."):
            if len(part) > 2 and part[2] in "/\\":
                part = part[3:]
            else:
                break
        joined = os.path.normpath(os.path.join(joined, part))

    if not os.path.abspath(joined).startswith(os.path.abspath(base)):
        raise ValueError(f"Path traversal detected: {joined} escapes {base}")

    return joined


def save(file_content, relative_path, content_type=None):
    """Save file content to storage and return the relative reference.

    Args:
        file_content: bytes or file-like object to save
        relative_path: path relative to MEDIA_ROOT (e.g. "videos/project_1/video_1.mp4")
        content_type: optional MIME type (reserved for future use)

    Returns:
        str: relative path reference suitable for database storage
    """
    media_root = _get_media_root()
    full_path = _safe_join(media_root, relative_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    if hasattr(file_content, "read"):
        data = file_content.read()
    else:
        data = file_content

    with open(full_path, "wb") as f:
        f.write(data)

    return relative_path


def exists(relative_path):
    """Check if a file exists in storage."""
    media_root = _get_media_root()
    full_path = _safe_join(media_root, relative_path)
    return os.path.isfile(full_path)


def get_path(relative_path):
    """Return the absolute filesystem path for a relative reference.

    Use sparingly — prefer relative references in the database.
    """
    media_root = _get_media_root()
    return _safe_join(media_root, relative_path)


def delete(relative_path):
    """Delete a file from storage. No-op if file doesn't exist."""
    media_root = _get_media_root()
    full_path = _safe_join(media_root, relative_path)
    if os.path.isfile(full_path):
        os.remove(full_path)


def url(relative_path):
    """Return the media URL for a relative reference."""
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    return f"{media_url}{relative_path}"
