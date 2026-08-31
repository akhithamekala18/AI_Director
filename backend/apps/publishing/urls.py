# -*- coding: utf-8 -*-
from django.urls import path
from .views import (SocialAccountListView, SocialAccountConnectView, SocialAccountDisconnectView, PendingApprovalsView, RecheckApprovalsView)

urlpatterns = [
    path("social-accounts/", SocialAccountListView.as_view(), name="social-account-list"),
    path("social-accounts/connect/", SocialAccountConnectView.as_view(), name="social-account-connect"),
    path("social-accounts/<int:pk>/disconnect/", SocialAccountDisconnectView.as_view(), name="social-account-disconnect"),
    path("pending-approvals/", PendingApprovalsView.as_view(), name="pending-approvals"),
    path("recheck-approvals/", RecheckApprovalsView.as_view(), name="recheck-approvals"),
]
