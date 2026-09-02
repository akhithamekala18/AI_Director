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
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# Celery test configuration: run tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# AI provider test configuration (mock, no real API calls)
AI_PROVIDER = "openai"
OPENAI_API_KEY = "test-key-not-real"
OPENAI_MODEL = "gpt-4o"

# Redis not required for unit tests
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
