# -*- coding: utf-8 -*-
"""OAuth views for social platform authorization (DG-11).

Implements the OAuth authorization-code flow:
1. User clicks "Connect" -> GET /api/publishing/oauth/{platform}/
2. Redirects to platform authorization URL
3. Platform redirects back to callback
4. Backend exchanges code for tokens
5. Tokens encrypted and stored on SocialAccount
6. User redirected to settings page
"""
import hashlib
import hmac
import logging
import secrets
import time

from django.conf import settings
from django.http import HttpResponseRedirect
from django.views import View

from apps.settings_app.services import decrypt_secret, encrypt_secret

from .adapters.registry import get_adapter
from .services import connect_social_account

logger = logging.getLogger("apps.publishing.oauth")

# In-memory state store (production would use Redis or session)
_oauth_states = {}


def _generate_state(user_id):
    """Generate a CSRF-safe state parameter."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": user_id,
        "created_at": time.time(),
    }
    return state


def _validate_state(state, user_id):
    """Validate and consume an OAuth state parameter."""
    data = _oauth_states.pop(state, None)
    if data is None:
        return False
    if data["user_id"] != user_id:
        return False
    if time.time() - data["created_at"] > 600:  # 10 min expiry
        return False
    return True


class OAuthStartView(View):
    """Initiate OAuth flow for a platform.

    GET /api/publishing/oauth/{platform}/
    """

    def get(self, request, platform):
        try:
            adapter = get_adapter(platform)
        except ValueError:
            from django.http import JsonResponse
            return JsonResponse({"error": f"Unsupported platform: {platform}"}, status=400)

        state = _generate_state(request.user.id)
        auth_url = adapter.get_authorization_url(state)

        return HttpResponseRedirect(auth_url)


class OAuthCallbackView(View):
    """Handle OAuth callback from platform.

    GET /api/publishing/oauth/{platform}/callback/
    """

    def get(self, request, platform):
        from django.http import JsonResponse

        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")

        if error:
            logger.warning("OAuth error for %s: %s", platform, error)
            return JsonResponse({"error": error}, status=400)

        if not code or not state:
            return JsonResponse({"error": "Missing code or state"}, status=400)

        if not _validate_state(state, request.user.id):
            return JsonResponse({"error": "Invalid or expired state"}, status=400)

        try:
            adapter = get_adapter(platform)

            # Exchange code for tokens
            token_data = adapter.exchange_code(code)

            # Get account info
            account_info = adapter.get_account_info(token_data.access_token)

            # Encrypt tokens before storage
            encrypted_tokens = {
                "access_token": encrypt_secret(token_data.access_token),
                "token_type": token_data.token_type,
                "expires_in": token_data.expires_in,
                "scope": token_data.scope,
            }
            if token_data.refresh_token:
                encrypted_tokens["refresh_token"] = encrypt_secret(token_data.refresh_token)

            # Connect account (updates encrypted_tokens)
            account = connect_social_account(
                request.user,
                platform,
                account_info.platform_account_id,
                account_info.display_name,
            )
            account.encrypted_tokens = encrypted_tokens
            account.save()

            logger.info("OAuth success: %s account %s connected for user %s",
                       platform, account_info.platform_account_id, request.user.id)

            # Redirect to settings page
            return HttpResponseRedirect("/settings?oauth=success")

        except Exception as exc:
            logger.error("OAuth callback failed for %s: %s", platform, exc)
            return JsonResponse({"error": f"OAuth failed: {str(exc)}"}, status=500)
