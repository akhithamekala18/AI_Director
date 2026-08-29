# -*- coding: utf-8 -*-
from django.urls import path

from apps.settings_app.views import (
    CredentialCreateView,
    CredentialListView,
    CredentialRevokeView,
    SettingsView,
)

urlpatterns = [
    path("", SettingsView.as_view(), name="settings"),
    path("credentials/", CredentialListView.as_view(), name="credential-list"),
    path("credentials/create/", CredentialCreateView.as_view(), name="credential-create"),
    path("credentials/<int:pk>/revoke/", CredentialRevokeView.as_view(), name="credential-revoke"),
]
