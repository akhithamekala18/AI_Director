# -*- coding: utf-8 -*-
"""
Hermetic test settings.

Database: switches to an in-memory SQLite store so the automated suite runs
without requiring a live PostgreSQL instance. The ORM is unchanged, so all
models/constraints still work identically; production remains PostgreSQL per
decision log DG-3. Documented as a foundation decision in the audit reports.
"""
from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"
CREDENTIAL_ENCRYPTION_KEY = "test-credential-encryption-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}