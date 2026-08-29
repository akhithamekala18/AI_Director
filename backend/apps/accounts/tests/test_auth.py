# -*- coding: utf-8 -*-
"""Authentication foundation tests (Development Plan Day 4)."""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def anon_client():
    return APIClient()


def test_register_then_login_succeeds(anon_client, db):
    resp = anon_client.post("/api/accounts/register/", {
        "username": "newbie",
        "email": "newbie@example.com",
        "password": "Str0ngPass!!",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["token"]
    assert body["data"]["user"]["username"] == "newbie"

    login = anon_client.post("/api/accounts/login/", {"username": "newbie", "password": "Str0ngPass!!"})
    assert login.status_code == 200
    assert login.json()["data"]["token"]


def test_invalid_login_is_rejected(anon_client, make_user):
    make_user(username="bob", password="RightPass123!")
    resp = anon_client.post("/api/accounts/login/", {"username": "bob", "password": "WrongPass999"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_unauthenticated_request_rejected(anon_client):
    resp = anon_client.get("/api/projects/")
    assert resp.status_code in (401, 403)


def test_me_returns_role(api_client):
    client = api_client(role="Creator")
    resp = client.get("/api/accounts/me/")
    assert resp.status_code == 200
    assert resp.json()["data"]["user"]["role"] == "Creator"


def test_protected_route_after_logout_requires_auth(make_user):
    from django.contrib.auth import get_user_model

    user = make_user(username="logout_user")
    client = APIClient()
    assert client.login(username="logout_user", password="LongPass123!")
    # Logout through the API needs the token; use the token API path.
    token = _token(user)
    aclient = APIClient()
    aclient.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    out = aclient.post("/api/accounts/logout/")
    assert out.status_code == 200
    aclient.credentials()
    denied = aclient.get("/api/projects/")
    assert denied.status_code in (401, 403)


def _token(user):
    from rest_framework.authtoken.models import Token

    t, _ = Token.objects.get_or_create(user=user)
    return t.key


def test_password_is_not_stored_in_plaintext(make_user):
    from django.contrib.auth import get_user_model

    make_user(username="hashcheck", password="AnotherPass123!")
    user = get_user_model().objects.get(username="hashcheck")
    assert user.password != "AnotherPass123!"
    assert user.password.startswith(("pbkdf2", "scrypt", "bcrypt", "argon2"))


def test_duplicate_username_registration_rejected(anon_client, make_user):
    make_user(username="dup")
    resp = anon_client.post("/api/accounts/register/", {
        "username": "dup", "email": "dup@example.com", "password": "Str0ngPass!!",
    })
    assert resp.status_code == 400
    assert resp.json()["success"] is False
