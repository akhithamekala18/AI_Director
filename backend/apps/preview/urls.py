# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    PreviewApproveView,
    PreviewDetailView,
    PreviewGenerateView,
    PreviewListView,
    PreviewRejectView,
)

urlpatterns = [
    path("generate/", PreviewGenerateView.as_view(), name="preview-generate"),
    path("", PreviewListView.as_view(), name="preview-list"),
    path("<int:preview_id>/", PreviewDetailView.as_view(), name="preview-detail"),
    path(
        "<int:preview_id>/approve/",
        PreviewApproveView.as_view(),
        name="preview-approve",
    ),
    path(
        "<int:preview_id>/reject/",
        PreviewRejectView.as_view(),
        name="preview-reject",
    ),
]
