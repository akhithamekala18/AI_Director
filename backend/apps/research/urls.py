# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    ResearchApproveView,
    ResearchDetailView,
    ResearchGapsView,
    ResearchGenerateView,
    ResearchRequestChangesView,
    ResearchSourcesView,
)

urlpatterns = [
    path("generate/", ResearchGenerateView.as_view(), name="research-generate"),
    path("", ResearchDetailView.as_view(), name="research-detail"),
    path("sources/", ResearchSourcesView.as_view(), name="research-sources"),
    path("approve/", ResearchApproveView.as_view(), name="research-approve"),
    path(
        "request-changes/",
        ResearchRequestChangesView.as_view(),
        name="research-request-changes",
    ),
    path("gaps/", ResearchGapsView.as_view(), name="research-gaps"),
]
