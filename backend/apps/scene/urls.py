# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    SceneApproveView,
    SceneBuildView,
    SceneDetailView,
    SceneRequestChangesView,
)

urlpatterns = [
    path("build/", SceneBuildView.as_view(), name="scene-build"),
    path("", SceneDetailView.as_view(), name="scene-detail"),
    path("approve/", SceneApproveView.as_view(), name="scene-approve"),
    path(
        "request-changes/",
        SceneRequestChangesView.as_view(),
        name="scene-request-changes",
    ),
]
