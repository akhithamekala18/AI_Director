# -*- coding: utf-8 -*-
"""Instagram adapter (Meta OAuth + Instagram Graph API).

Required environment variables:
  INSTAGRAM_CLIENT_ID
  INSTAGRAM_CLIENT_SECRET
  INSTAGRAM_REDIRECT_URI
"""
import json
import logging
import os

import httpx

from .base import AccountInfo, PlatformAdapter, PublishResult, TokenData

logger = logging.getLogger("apps.publishing.instagram")

INSTAGRAM_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
INSTAGRAM_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
INSTAGRAM_API_BASE = "https://graph.facebook.com/v18.0"
INSTAGRAM_SCOPES = ["instagram_basic", "instagram_content_publish", "pages_show_list"]


class InstagramAdapter(PlatformAdapter):
    platform = "Instagram"

    def _client_id(self):
        return os.environ.get("INSTAGRAM_CLIENT_ID", "")

    def _client_secret(self):
        return os.environ.get("INSTAGRAM_CLIENT_SECRET", "")

    def _redirect_uri(self):
        return os.environ.get("INSTAGRAM_REDIRECT_URI", "http://localhost:8000/api/publishing/oauth/instagram/callback/")

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id(),
            "redirect_uri": self._redirect_uri(),
            "scope": ",".join(INSTAGRAM_SCOPES),
            "state": state,
            "response_type": "code",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{INSTAGRAM_AUTH_URL}?{query}"

    def exchange_code(self, code: str) -> TokenData:
        with httpx.Client(timeout=30) as client:
            resp = client.get(INSTAGRAM_TOKEN_URL, params={
                "client_id": self._client_id(),
                "client_secret": self._client_secret(),
                "redirect_uri": self._redirect_uri(),
                "code": code,
            })
            resp.raise_for_status()
            data = resp.json()
            return TokenData(
                access_token=data["access_token"],
                expires_in=data.get("expires_in", 3600),
                token_type="Bearer",
            )

    def refresh_access_token(self, refresh_token: str) -> TokenData:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{INSTAGRAM_API_BASE}/oauth/access_token", params={
                "grant_type": "fb_exchange_token",
                "client_id": self._client_id(),
                "client_secret": self._client_secret(),
                "fb_exchange_token": refresh_token,
            })
            resp.raise_for_status()
            data = resp.json()
            return TokenData(
                access_token=data["access_token"],
                expires_in=data.get("expires_in", 3600),
            )

    def get_account_info(self, access_token: str) -> AccountInfo:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{INSTAGRAM_API_BASE}/me",
                params={"fields": "id,name", "access_token": access_token},
            )
            resp.raise_for_status()
            data = resp.json()
            return AccountInfo(
                platform="Instagram",
                platform_account_id=data["id"],
                display_name=data.get("name", ""),
            )

    def upload_media(self, access_token: str, file_path: str, metadata: dict) -> str:
        """Instagram requires a two-step upload: create container, then publish."""
        caption = metadata.get("caption", "")
        with httpx.Client(timeout=60) as client:
            # Step 1: Create media container
            resp = client.post(
                f"{INSTAGRAM_API_BASE}/me/media",
                data={
                    "media_type": "VIDEO",
                    "video_url": metadata.get("video_url", ""),
                    "caption": caption[:2200],
                    "access_token": access_token,
                },
            )
            resp.raise_for_status()
            container_id = resp.json()["id"]

            # Step 2: Wait for processing (simplified — real impl would poll)
            import time
            time.sleep(5)

            # Step 3: Publish
            resp = client.post(
                f"{INSTAGRAM_API_BASE}/me/media_publish",
                data={
                    "creation_id": container_id,
                    "access_token": access_token,
                },
            )
            resp.raise_for_status()
            return resp.json()["id"]

    def publish(self, access_token: str, media_id: str, metadata: dict) -> PublishResult:
        return PublishResult(
            success=True,
            platform="Instagram",
            platform_post_id=media_id,
            published_url=f"https://instagram.com/p/{media_id}",
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
        return PublishResult(success=False, platform="Instagram", error_code=error_code, error_message=error_message, retryable=retryable)
