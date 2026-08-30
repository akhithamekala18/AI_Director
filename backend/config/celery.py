# -*- coding: utf-8 -*-
"""Celery application configuration (DG-8 resolved: Celery + Redis).

Configures Celery for Django with Redis as the message broker.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("ai_director")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Queue configuration
app.conf.task_routes = {
    "apps.ai_orchestration.tasks.*": {"queue": "default"},
}

# Retry configuration
app.conf.task_default_retry_delay = 60  # 1 minute
app.conf.task_max_retries = 3

# Time limits
app.conf.task_soft_time_limit = 300  # 5 minutes
app.conf.task_time_limit = 600  # 10 minutes

# Result backend
app.conf.result_backend = "django-db"
app.conf.result_expires = 86400  # 24 hours


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f"Request: {self.request!r}")
