# -*- coding: utf-8 -*-
"""Settings foundation + encrypted credential store tests (Day 7, §29.4)."""
import pytest

from apps.settings_app.models import StoredCredential
from apps.settings_app.services import decrypt_secret, encrypt_secret


def test_settings_get_then_patch_persists(api_client):
    client = api_client(role="Creator")
    get = client.get("/api/settings/")
    assert get.status_code == 200
    sid = get.json()["data"]["settings"]["id"]
    patch = client.patch("/api/settings/", {"default_voice_style": "warm"})
    assert patch.status_code == 200
    assert patch.json()["data"]["settings"]["default_voice_style"] == "warm"
    assert patch.json()["data"]["settings"]["id"] == sid


def test_credential_round_trip_encrypt_decrypt():
    ciphertext = encrypt_secret("super-secret-platform-token")
    assert ciphertext != "super-secret-platform-token"
    assert decrypt_secret(ciphertext) == "super-secret-platform-token"


def test_credential_api_never_exposes_secret(api_client):
    client = api_client(role="Creator")
    create = client.post("/api/settings/credentials/create/", {
        "provider": "social",
        "label": "main",
        "secret": "should-never-be-returned",
    })
    assert create.status_code == 201
    body = create.json()["data"]["credential"]
    assert "secret" not in body
    assert "encrypted_value" not in body
    raw = " ".join(str(body).lower().split())
    assert "should-never-be-returned" not in raw


def test_credential_revoke(api_client):
    client = api_client(role="Creator")
    cid = client.post("/api/settings/credentials/create/", {
        "provider": "social", "label": "main", "secret": "token",
    }).json()["data"]["credential"]["id"]
    revoke = client.post(f"/api/settings/credentials/{cid}/revoke/")
    assert revoke.status_code == 200
    assert revoke.json()["data"]["credential"]["revoked"] is True
    listing = client.get("/api/settings/credentials/").json()["data"]["credentials"]
    assert cid not in [c["id"] for c in listing]


def test_credential_at_rest_is_ciphertext(make_user):
    from apps.accounts.models import Team

    user = make_user(username="cred_owner")
    from django.contrib.auth import get_user_model
    token = encrypt_secret("roundtrip-token")
    team = Team.objects.first() or Team.objects.create(name="x")
    StoredCredential.objects.create(owner=user, provider="p", label="l", encrypted_value=token)
    stored = StoredCredential.objects.get(provider="p")
    assert stored.encrypted_value != "roundtrip-token"
    assert decrypt_secret(stored.encrypted_value) == "roundtrip-token"
