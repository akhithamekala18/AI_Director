# -*- coding: utf-8 -*-
from django.urls import path
from .views import (SocialAccountListView, SocialAccountConnectView, SocialAccountDisconnectView, PendingApprovalsView, RecheckApprovalsView)
from .oauth import OAuthStartView, OAuthCallbackView

urlpatterns = [
    path("social-accounts/", SocialAccountListView.as_view(), name="social-account-list"),
    path("social-accounts/connect/", SocialAccountConnectView.as_view(), name="social-account-connect"),
    path("social-accounts/<int:pk>/disconnect/", SocialAccountDisconnectView.as_view(), name="social-account-disconnect"),
    path("pending-approvals/", PendingApprovalsView.as_view(), name="pending-approvals"),
    path("recheck-approvals/", RecheckApprovalsView.as_view(), name="recheck-approvals"),
    path("oauth/<str:platform>/", OAuthStartView.as_view(), name="oauth-start"),
    path("oauth/<str:platform>/callback/", OAuthCallbackView.as_view(), name="oauth-callback"),
]
