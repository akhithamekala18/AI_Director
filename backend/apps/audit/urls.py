# -*- coding: utf-8 -*-
from django.urls import path

from apps.audit.views import AuditLogListView

urlpatterns = [
    path("logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("", AuditLogListView.as_view(), name="audit-browse"),
]
