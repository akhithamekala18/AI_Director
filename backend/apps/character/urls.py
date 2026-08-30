# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    CharacterApproveView,
    CharacterDetailView,
    CharacterGenerateView,
    CharacterLibraryView,
    CharacterRequestChangesView,
    CharacterReuseView,
)

urlpatterns = [
    path("generate/", CharacterGenerateView.as_view(), name="character-generate"),
    path("", CharacterDetailView.as_view(), name="character-detail"),
    path("approve/", CharacterApproveView.as_view(), name="character-approve"),
    path(
        "request-changes/",
        CharacterRequestChangesView.as_view(),
        name="character-request-changes",
    ),
    path("library/", CharacterLibraryView.as_view(), name="character-library"),
    path("reuse/", CharacterReuseView.as_view(), name="character-reuse"),
]
