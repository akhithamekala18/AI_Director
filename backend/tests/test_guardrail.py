# -*- coding: utf-8 -*-
"""Guardrail structural test (Development Plan Day 11/B1 exit, §35.5).

Guarantees that no automated publishing or upload endpoint exists in the
foundation. Zero unapproved uploads is a guardrail metric; in B1 the publishing
path is structurally absent, so nothing can bypass approval.
"""
from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver


def _iter_patterns(patterns):
    for pattern in patterns:
        if isinstance(pattern, URLPattern):
            yield pattern
        elif isinstance(pattern, URLResolver):
            yield from _iter_patterns(pattern.url_patterns)


def test_no_publishing_or_upload_endpoint_exists():
    resolver = get_resolver()
    names = []
    for pattern in _iter_patterns(resolver.url_patterns):
        names.append(pattern.name or "")
    joined = " ".join(names).lower()
    for forbidden in ["publish", "upload", "schedule-publish"]:
        assert forbidden not in joined, f"forbidden endpoint keyword present: {forbidden}"


def test_publishing_is_disabled_in_foundation():
    assert settings.PUBLISHING_ENABLED is False
