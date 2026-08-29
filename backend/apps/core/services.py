# -*- coding: utf-8 -*-
"""Core services for the Phase-1 foundation.

storage_access_token() provides signed-delivery readiness (Development Plan
Day 10, Overview §29.6), producing a short-lived HMAC token bound to an artifact
key so that media URLs cannot be read without a valid grant. Publishing
credentials encryption lives in apps.settings_app.services.
"""
import hashlib
import hmac
import time

from django.conf import settings


def storage_access_token(artifact_key, ttl_seconds=300):
    """Return a signed token (key, expiry) proving a read grant for artifact_key.

    Deterministic, time-boxed, and validated by validate_storage_access_token.
    The encryption key is sourced from CREDENTIAL_ENCRYPTION_KEY in settings.
    """
    expires = int(time.time()) + int(ttl_seconds)
    message = f"{artifact_key}:{expires}".encode("utf-8")
    signature = hmac.new(
        settings.CREDENTIAL_ENCRYPTION_KEY.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    return {"artifact_key": artifact_key, "expires": expires, "signature": signature}


def validate_storage_access_token(artifact_key, expires, signature, now=None):
    """Return True if the token is valid and not expired for artifact_key."""
    now = now if now is not None else int(time.time())
    if int(expires) < now:
        return False
    message = f"{artifact_key}:{expires}".encode("utf-8")
    expected = hmac.new(
        settings.CREDENTIAL_ENCRYPTION_KEY.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")
