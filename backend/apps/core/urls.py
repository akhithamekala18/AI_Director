# -*- coding: utf-8 -*-
from django.urls import path

from apps.core.views import HealthzView, StorageTokenView

urlpatterns = [
    path("healthz/", HealthzView.as_view(), name="healthz"),
    path("storage/token/", StorageTokenView.as_view(), name="storage-token"),
]
