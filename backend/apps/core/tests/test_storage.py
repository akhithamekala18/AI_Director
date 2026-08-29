# -*- coding: utf-8 -*-
"""Storage access-control tests (Development Plan Day 10, Overview §29.6)."""
from apps.core.services import storage_access_token, validate_storage_access_token


def test_storage_token_round_trip_valid(db):
    token = storage_access_token("video/scene1.mp4", ttl_seconds=300)
    assert validate_storage_access_token(token["artifact_key"], token["expires"], token["signature"]) is True


def test_storage_token_rejects_expired(db):
    token = storage_access_token("video/scene2.mp4", ttl_seconds=1)
    assert validate_storage_access_token(
        token["artifact_key"], token["expires"], token["signature"], now=token["expires"] + 2
    ) is False


def test_storage_token_rejects_wrong_key(db):
    token = storage_access_token("video/scene3.mp4")
    assert validate_storage_access_token("video/other.mp4", token["expires"], token["signature"]) is False


def test_storage_token_rejects_forged_signature(db):
    token = storage_access_token("video/scene4.mp4")
    assert validate_storage_access_token(token["artifact_key"], token["expires"], "forged") is False
