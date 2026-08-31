# -*- coding: utf-8 -*-
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

@pytest.fixture
def user(make_user):
    return make_user(username="pub_user", role="Approver/Owner")

@pytest.fixture
def team(user):
    return user.memberships.first().team

@pytest.fixture
def project(user, team):
    from apps.projects.models import Project
    return Project.objects.create(topic="Test Publishing Project", team=team, owner=user)

@pytest.fixture
def auth_client(make_user, user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client

@pytest.fixture
def outsider_client(make_user):
    outsider = make_user(username="pub_outsider", role="Creator")
    token, _ = Token.objects.get_or_create(user=outsider)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = outsider
    return client

@pytest.fixture
def social_account(user, team):
    from apps.publishing.models import SocialAccount
    return SocialAccount.objects.create(
        owner=user, team=team, platform="YouTube",
        platform_account_id="yt_12345", display_name="Test YouTube",
    )

@pytest.fixture
def post(user, project):
    from apps.publishing.models import ScheduledPost
    return ScheduledPost.objects.create(
        project=project, team=user.memberships.first().team,
        owner=user, status="draft",
    )

@pytest.fixture
def scheduled_entry(user, project, post, social_account):
    from apps.publishing.models import ScheduledEntry
    from django.utils import timezone
    from datetime import timedelta
    return ScheduledEntry.objects.create(
        post=post, social_account=social_account, platform="YouTube",
        team=user.memberships.first().team, status="scheduled",
        scheduled_utc=timezone.now() + timedelta(hours=48),
    )
