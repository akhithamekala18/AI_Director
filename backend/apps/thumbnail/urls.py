# -*- coding: utf-8 -*-
from django.urls import path

from .views import ThumbnailDetailView, ThumbnailGenerateView, ThumbnailListView

urlpatterns = [
    path("generate/", ThumbnailGenerateView.as_view(), name="thumbnail-generate"),
    path("", ThumbnailListView.as_view(), name="thumbnail-list"),
    path("<int:thumbnail_id>/", ThumbnailDetailView.as_view(), name="thumbnail-detail"),
]
