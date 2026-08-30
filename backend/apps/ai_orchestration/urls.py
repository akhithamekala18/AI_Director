# -*- coding: utf-8 -*-
from django.urls import path

from .views import JobCancelView, JobDetailView, JobListCreateView, JobRetryView

urlpatterns = [
    path("jobs/", JobListCreateView.as_view(), name="job-list-create"),
    path("jobs/<int:pk>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<int:pk>/cancel/", JobCancelView.as_view(), name="job-cancel"),
    path("jobs/<int:pk>/retry/", JobRetryView.as_view(), name="job-retry"),
]
