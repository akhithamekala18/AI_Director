# -*- coding: utf-8 -*-
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta


@pytest.fixture
def user(make_user):
    return make_user(username="analytics_user", role="Approver/Owner")


@pytest.fixture
def team(user):
    return user.memberships.first().team


@pytest.fixture
def project(user, team):
    from apps.projects.models import Project
    return Project.objects.create(topic="Analytics Test Project", team=team, owner=user)


@pytest.fixture
def auth_client(make_user, user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client


@pytest.fixture
def outsider_client(make_user):
    outsider = make_user(username="analytics_outsider", role="Creator")
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
        platform_account_id="yt_analytics_1", display_name="Analytics YT",
    )


@pytest.fixture
def published_entry(user, project, social_account, team):
    from apps.publishing.models import ScheduledEntry, ScheduledPost
    post = ScheduledPost.objects.create(
        project=project, team=team, owner=user, status="published"
    )
    return ScheduledEntry.objects.create(
        post=post, social_account=social_account, platform="YouTube",
        team=team, status="published",
        scheduled_utc=timezone.now() + timedelta(hours=48),
    )


@pytest.fixture
def unpublished_entry(user, project, social_account, team):
    from apps.publishing.models import ScheduledEntry, ScheduledPost
    post = ScheduledPost.objects.create(
        project=project, team=team, owner=user, status="draft"
    )
    return ScheduledEntry.objects.create(
        post=post, social_account=social_account, platform="Instagram",
        team=team, status="scheduled",
        scheduled_utc=timezone.now() + timedelta(hours=24),
    )
