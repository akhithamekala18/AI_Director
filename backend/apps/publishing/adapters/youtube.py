# -*- coding: utf-8 -*-
"""YouTube adapter (Google OAuth2 + YouTube Data API v3).

Implements the PlatformAdapter interface for YouTube publishing.
Uses httpx for HTTP requests (already in project dependencies).

Required environment variables:
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REDIRECT_URI
"""
import logging
import os

import httpx

from .base import AccountInfo, PlatformAdapter, PublishResult, TokenData

logger = logging.getLogger("apps.publishing.youtube")

YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class YouTubeAdapter(PlatformAdapter):
    """YouTube publishing adapter using Google OAuth2 + Data API v3."""

    platform = "YouTube"

    def _client_id(self):
        return os.environ.get("YOUTUBE_CLIENT_ID", "")

    def _client_secret(self):
        return os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    def _redirect_uri(self):
        return os.environ.get("YOUTUBE_REDIRECT_URI", "http://localhost:8000/api/publishing/oauth/youtube/callback/")

    def get_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._client_id(),
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{YOUTUBE_AUTH_URL}?{query}"

    def exchange_code(self, code: str) -> TokenData:
        with httpx.Client(timeout=30) as client:
            resp = client.post(YOUTUBE_TOKEN_URL, data={
                "code": code,
                "client_id": self._client_id(),
                "client_secret": self._client_secret(),
                "redirect_uri": self._redirect_uri(),
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            data = resp.json()
            return TokenData(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                expires_in=data.get("expires_in", 3600),
                token_type=data.get("token_type", "Bearer"),
                scope=data.get("scope", ""),
            )

    def refresh_access_token(self, refresh_token: str) -> TokenData:
        with httpx.Client(timeout=30) as client:
            resp = client.post(YOUTUBE_TOKEN_URL, data={
                "refresh_token": refresh_token,
                "client_id": self._client_id(),
                "client_secret": self._client_secret(),
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            data = resp.json()
            return TokenData(
                access_token=data["access_token"],
                refresh_token=refresh_token,
                expires_in=data.get("expires_in", 3600),
                token_type=data.get("token_type", "Bearer"),
                scope=data.get("scope", ""),
            )

    def get_account_info(self, access_token: str) -> AccountInfo:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={"part": "snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                raise ValueError("No YouTube channel found")
            snippet = items[0]["snippet"]
            return AccountInfo(
                platform="YouTube",
                platform_account_id=items[0]["id"],
                display_name=snippet.get("title", ""),
                provider_metadata={"channel_title": snippet.get("title", "")},
            )

    def upload_media(self, access_token: str, file_path: str, metadata: dict) -> str:
        """Upload video to YouTube using resumable upload protocol."""
        title = metadata.get("title", "AI Director Video")
        description = metadata.get("description", "")
        tags = metadata.get("tags", [])
        privacy = metadata.get("privacy_status", "private")

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        import json
        with httpx.Client(timeout=60) as client:
            # Initiate resumable upload
            resp = client.post(
                f"{YOUTUBE_API_BASE}/videos",
                params={"uploadType": "resumable", "part": "snippet,status"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Upload-Content-Type": "video/mp4",
                },
                content=json.dumps(body),
            )
            resp.raise_for_status()
            upload_url = resp.headers.get("Location", "")

            # Upload the file
            import os
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                upload_resp = client.put(
                    upload_url,
                    headers={
                        "Content-Length": str(file_size),
                        "Content-Type": "video/mp4",
                    },
                    content=f,
                )
                upload_resp.raise_for_status()
                result = upload_resp.json()
                return result["id"]

    def publish(self, access_token: str, media_id: str, metadata: dict) -> PublishResult:
        """YouTube videos are published on upload (privacy status controls visibility)."""
        return PublishResult(
            success=True,
            platform="YouTube",
            platform_post_id=media_id,
            published_url=f"https://youtube.com/watch?v={media_id}",
            provider_metadata={"upload_type": "resumable"},
        )

    def normalize_error(self, exc: Exception) -> PublishResult:
        error_code = ""
        error_message = str(exc)
        retryable = False

        if hasattr(exc, "response"):
            resp = exc.response
            if hasattr(resp, "status_code"):
                error_code = str(resp.status_code)
                if resp.status_code == 401:
                    error_message = "Authentication failed - token may be expired"
                    retryable = True
                elif resp.status_code == 403:
                    error_message = "Insufficient permissions"
                    retryable = False
                elif resp.status_code == 429:
                    error_message = "Rate limit exceeded"
                    retryable = True
                elif resp.status_code >= 500:
                    error_message = "YouTube server error"
                    retryable = True

        return PublishResult(
            success=False,
            platform="YouTube",
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
        )
