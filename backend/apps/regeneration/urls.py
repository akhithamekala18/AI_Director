# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    RegenerationCreateView,
    RegenerationDetailView,
    RegenerationListView,
)

urlpatterns = [
    path("regenerate/", RegenerationCreateView.as_view(), name="regeneration-create"),
    path("", RegenerationListView.as_view(), name="regeneration-list"),
    path(
        "<int:request_id>/",
        RegenerationDetailView.as_view(),
        name="regeneration-detail",
    ),
]
