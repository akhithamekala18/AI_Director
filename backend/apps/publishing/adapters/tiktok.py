# -*- coding: utf-8 -*-
"""TikTok adapter (TikTok Login Kit + Content Posting API).

Required environment variables:
  TIKTOK_CLIENT_KEY
  TIKTOK_CLIENT_SECRET
  TIKTOK_REDIRECT_URI
"""
import json
import logging
import os

import httpx

from .base import AccountInfo, PlatformAdapter, PublishResult, TokenData

logger = logging.getLogger("apps.publishing.tiktok")

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"
TIKTOK_SCOPES = ["user.info.basic", "video.upload", "video.publish"]


class TikTokAdapter(PlatformAdapter):
    platform = "TikTok"

    def _client_key(self):
        return os.environ.get("TIKTOK_CLIENT_KEY", "")

    def _client_secret(self):
        return os.environ.get("TIKTOK_CLIENT_SECRET", "")

    def _redirect_uri(self):
        return os.environ.get("TIKTOK_REDIRECT_URI", "http://localhost:8000/api/publishing/oauth/tiktok/callback/")

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_key": self._client_key(),
            "scope": ",".join(TIKTOK_SCOPES),
            "response_type": "code",
            "redirect_uri": self._redirect_uri(),
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{TIKTOK_AUTH_URL}?{query}"

    def exchange_code(self, code: str) -> TokenData:
        with httpx.Client(timeout=30) as client:
            resp = client.post(TIKTOK_TOKEN_URL, data={
                "client_key": self._client_key(),
                "client_secret": self._client_secret(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._redirect_uri(),
            })
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return TokenData(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                expires_in=data.get("expires_in", 3600),
                token_type="Bearer",
                scope=data.get("scope", ""),
            )

    def refresh_access_token(self, refresh_token: str) -> TokenData:
        with httpx.Client(timeout=30) as client:
            resp = client.post(TIKTOK_TOKEN_URL, data={
                "client_key": self._client_key(),
                "client_secret": self._client_secret(),
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            })
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return TokenData(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", refresh_token),
                expires_in=data.get("expires_in", 3600),
            )

    def get_account_info(self, access_token: str) -> AccountInfo:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{TIKTOK_API_BASE}/user/info/",
                params={"fields": "open_id,display_name"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            user = data.get("user", {})
            return AccountInfo(
                platform="TikTok",
                platform_account_id=user.get("open_id", ""),
                display_name=user.get("display_name", ""),
            )

    def upload_media(self, access_token: str, file_path: str, metadata: dict) -> str:
        """TikTok: init upload, upload video, then publish."""
        with httpx.Client(timeout=60) as client:
            # Step 1: Init upload
            resp = client.post(
                f"{TIKTOK_API_BASE}/post/publish/video/init/",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "post_info": {
                        "title": metadata.get("title", "")[:150],
                        "privacy_level": metadata.get("privacy_level", "PUBLIC_TO_EVERYONE"),
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": os.path.getsize(file_path),
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            upload_url = data.get("upload_url", "")
            publish_id = data.get("publish_id", "")

            # Step 2: Upload video file
            with open(file_path, "rb") as f:
                upload_resp = client.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes 0-{os.path.getsize(file_path) - 1}/{os.path.getsize(file_path)}",
                    },
                    content=f,
                )
                upload_resp.raise_for_status()

            return publish_id

    def publish(self, access_token: str, media_id: str, metadata: dict) -> PublishResult:
        """TikTok publishing is done during upload_media (init+upload is the publish)."""
        return PublishResult(
            success=True,
            platform="TikTok",
            platform_post_id=media_id,
            published_url=f"https://tiktok.com/@me/video/{media_id}",
        )

    def normalize_error(self, exc: Exception) -> PublishResult:
        error_code = ""
        error_message = str(exc)
        retryable = False
        if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
            code = exc.response.status_code
            error_code = str(code)
            if code == 401:
                retryable = True
            elif code == 429:
                retryable = True
            elif code >= 500:
                retryable = True
        return PublishResult(success=False, platform="TikTok", error_code=error_code, error_message=error_message, retryable=retryable)
