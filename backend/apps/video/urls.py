# -*- coding: utf-8 -*-
from django.urls import path

from .views import VideoDetailView, VideoGenerateView, VideoListView

urlpatterns = [
    path("generate/", VideoGenerateView.as_view(), name="video-generate"),
    path("", VideoListView.as_view(), name="video-list"),
    path("<int:video_id>/", VideoDetailView.as_view(), name="video-detail"),
]
