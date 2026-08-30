# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    ScriptApproveView,
    ScriptDetailView,
    ScriptGenerateView,
    ScriptRequestChangesView,
)

urlpatterns = [
    path("generate/", ScriptGenerateView.as_view(), name="script-generate"),
    path("", ScriptDetailView.as_view(), name="script-detail"),
    path("approve/", ScriptApproveView.as_view(), name="script-approve"),
    path(
        "request-changes/",
        ScriptRequestChangesView.as_view(),
        name="script-request-changes",
    ),
]
