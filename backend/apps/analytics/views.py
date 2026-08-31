# -*- coding: utf-8 -*-
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.permissions import HasCapability
from apps.analytics import services
from apps.analytics.serializers import AuditExportSerializer, PublishedPerformanceSerializer
from apps.core.response import ok


class AnalyticsSummaryView(GenericAPIView):
    """GET /api/analytics/summary/ - aggregated analytics across published entries."""
    permission_classes = [HasCapability]
    capability = "view_projects"

    def get(self, request, *args, **kwargs):
        team_id = request.query_params.get("team_id")
        summary = services.get_analytics_summary(request.user, team_id)
        return ok({"summary": summary})


class AnalyticsByPlatformView(GenericAPIView):
    """GET /api/analytics/by-platform/ - analytics grouped by platform."""
    permission_classes = [HasCapability]
    capability = "view_projects"

    def get(self, request, *args, **kwargs):
        team_id = request.query_params.get("team_id")
        data = services.get_analytics_by_platform(request.user, team_id)
        return ok({"platforms": list(data)})


class AnalyticsByTopicView(GenericAPIView):
    """GET /api/analytics/by-topic/ - analytics grouped by topic."""
    permission_classes = [HasCapability]
    capability = "view_projects"

    def get(self, request, *args, **kwargs):
        team_id = request.query_params.get("team_id")
        data = services.get_analytics_by_topic(request.user, team_id)
        return ok({"topics": list(data)})


class AnalyticsRecordView(GenericAPIView):
    """POST /api/analytics/record/ - record performance for a published entry."""
    serializer_class = PublishedPerformanceSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"

    def post(self, request, *args, **kwargs):
        entry_id = request.data.get("entry_id")
        if not entry_id:
            raise ValidationError("entry_id is required")
        from apps.publishing.models import ScheduledEntry
        entry = ScheduledEntry.objects.filter(id=entry_id).first()
        if not entry:
            raise NotFound("entry not found")
        try:
            obj = services.record_published_performance(
                entry,
                views=request.data.get("views", 0),
                likes=request.data.get("likes", 0),
                comments=request.data.get("comments", 0),
                shares=request.data.get("shares", 0),
                topic=request.data.get("topic", ""),
            )
        except ValueError as e:
            raise ValidationError(str(e)) from e
        return ok({"analytics": self.get_serializer(obj).data})


class AuditExportView(GenericAPIView):
    """POST /api/analytics/audit-export/ - export audit logs."""
    serializer_class = AuditExportSerializer
    permission_classes = [HasCapability]
    capability = "view_audit"

    def post(self, request, *args, **kwargs):
        fmt = request.data.get("format", "csv")
        if fmt not in ("csv", "json"):
            raise ValidationError("format must be 'csv' or 'json'")
        export, _ = services.export_audit_log(request.user, fmt)
        return ok({"export": self.get_serializer(export).data})
