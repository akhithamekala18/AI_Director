# -*- coding: utf-8 -*-
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team


@pytest.fixture
def make_user(db):
    """Create a user with a personal workspace team and Creator membership."""

    def _make(username="alice", email="alice@example.com", password="LongPass123!", role="Creator"):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username=username, email=email, password=password)
        team = Team.objects.create(name=f"{username} workspace")
        user.memberships.create(team=team, role=role)
        return user

    return _make


@pytest.fixture
def api_client(make_user):
    """Return an authenticated APIClient bound to a named user's token."""

    def _client(role="Creator", username=None):
        name = username or f"user_{abs(hash(role)) % 100000}"
        user = make_user(username=name, role=role)
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        client.user = user
        return client

    return _client
