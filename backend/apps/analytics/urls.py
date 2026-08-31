# -*- coding: utf-8 -*-
from django.urls import path

from apps.analytics.views import (
    AnalyticsByPlatformView,
    AnalyticsByTopicView,
    AnalyticsRecordView,
    AnalyticsSummaryView,
    AuditExportView,
)

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("by-platform/", AnalyticsByPlatformView.as_view(), name="analytics-by-platform"),
    path("by-topic/", AnalyticsByTopicView.as_view(), name="analytics-by-topic"),
    path("record/", AnalyticsRecordView.as_view(), name="analytics-record"),
    path("audit-export/", AuditExportView.as_view(), name="audit-export"),
]
