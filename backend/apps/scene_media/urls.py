# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    SceneMediaDetailView,
    SceneMediaGenerateView,
    SceneMediaListView,
)

urlpatterns = [
    path("generate/", SceneMediaGenerateView.as_view(), name="scene-media-generate"),
    path("", SceneMediaListView.as_view(), name="scene-media-list"),
    path("<int:media_id>/", SceneMediaDetailView.as_view(), name="scene-media-detail"),
]
