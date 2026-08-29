# -*- coding: utf-8 -*-
from django.urls import path

from apps.projects.views import (
    ProjectArchiveView,
    ProjectDetailView,
    ProjectDuplicateView,
    ProjectListCreateView,
    ProjectTemplateCreateView,
    ProjectTransitionView,
)

urlpatterns = [
    path("", ProjectListCreateView.as_view(), name="project-list"),
    path("<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<int:pk>/archive/", ProjectArchiveView.as_view(), name="project-archive"),
    path("<int:pk>/duplicate/", ProjectDuplicateView.as_view(), name="project-duplicate"),
    path("<int:pk>/from-template/", ProjectTemplateCreateView.as_view(), name="project-from-template"),
    path("<int:pk>/transition/", ProjectTransitionView.as_view(), name="project-transition"),
]
