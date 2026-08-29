# -*- coding: utf-8 -*-
"""Encrypted credential store (Development Plan Day 7, Overview §29.4).

Platform publishing credentials are encrypted at rest (Fernet) and are never
returned by the API or written to logs. The encryption key is loaded from the
environment (CREDENTIAL_ENCRYPTION_KEY); the service derives a stable Fernet key
from it so any non-empty secret works.
"""
import base64
import hashlib

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def _fernet():
    secret = settings.CREDENTIAL_ENCRYPTION_KEY or "insecure"
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("credential could not be decrypted") from exc
