# -*- coding: utf-8 -*-
"""Scheduler API views (Task 38).

Follows existing Phase 2F conventions: token auth, HasCapability,
membership-scoped 404, standard {success, data} envelope.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView

from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects.services import get_project

from . import services
from .serializers import (
    ScheduleCancelSerializer,
    ScheduleCreateSerializer,
    ScheduleEntrySerializer,
    ScheduleRescheduleSerializer,
)


def _run(operation):
    try:
        return operation()
    except DjangoValidationError as exc:
        messages = getattr(exc, "messages", None) or [str(exc)]
        raise ValidationError(" ".join(messages)) from exc


def _get_project(request, project_id):
    project = get_project(request.user, project_id)
    if not project:
        raise NotFound("project not found")
    return project


class ScheduleCreateView(GenericAPIView):
    """POST /api/projects/{id}/schedule/ (manage_projects)."""

    serializer_class = ScheduleEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        body = ScheduleCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry = _run(lambda: services.create_entry(
            request.user, project,
            body.validated_data["platform"],
            body.validated_data["scheduled_local_datetime"],
            body.validated_data.get("timezone", "UTC"),
        ))
        return ok({"entry": self.get_serializer(entry).data})


class ScheduleListView(GenericAPIView):
    """GET /api/projects/{id}/schedule/ (view_projects)."""

    serializer_class = ScheduleEntrySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        entries = services.list_entries(request.user, project)
        return ok({"entries": self.get_serializer(entries, many=True).data})


class ScheduleCalendarView(GenericAPIView):
    """GET /api/projects/{id}/schedule/calendar/ (view_projects)."""

    serializer_class = ScheduleEntrySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        entries = services.get_calendar_entries(request.user, project)
        return ok({"calendar": self.get_serializer(entries, many=True).data})


class ScheduleDetailView(GenericAPIView):
    """GET /api/projects/{id}/schedule/<entry_id>/ (view_projects)."""

    serializer_class = ScheduleEntrySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        entry = services.get_entry(self.request.user, self.kwargs["entry_id"])
        if not entry or entry.project_id != project.id:
            raise NotFound("schedule entry not found")
        return entry

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        entry = self.get_object(project)
        return ok({"entry": self.get_serializer(entry).data})


class ScheduleRescheduleView(GenericAPIView):
    """POST /api/projects/{id}/schedule/<entry_id>/reschedule/ (manage_projects)."""

    serializer_class = ScheduleEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        entry = services.get_entry(self.request.user, self.kwargs["entry_id"])
        if not entry or entry.project_id != project.id:
            raise NotFound("schedule entry not found")
        return entry

    def post(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        entry = self.get_object(project)
        body = ScheduleRescheduleSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry = _run(lambda: services.reschedule_entry(
            request.user, entry,
            body.validated_data["scheduled_local_datetime"],
            body.validated_data.get("timezone"),
        ))
        return ok({"entry": self.get_serializer(entry).data})


class ScheduleCancelView(GenericAPIView):
    """POST /api/projects/{id}/schedule/<entry_id>/cancel/ (manage_projects)."""

    serializer_class = ScheduleEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        entry = services.get_entry(self.request.user, self.kwargs["entry_id"])
        if not entry or entry.project_id != project.id:
            raise NotFound("schedule entry not found")
        return entry

    def post(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        entry = self.get_object(project)
        body = ScheduleCancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry = _run(lambda: services.cancel_entry(
            request.user, entry, body.validated_data.get("reason", ""),
        ))
        return ok({"entry": self.get_serializer(entry).data})


class ScheduleBestTimeView(GenericAPIView):
    """GET /api/projects/{id}/schedule/best-time/?platform=X (view_projects)."""

    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        platform = request.query_params.get("platform", "")
        if not platform:
            raise ValidationError("platform query parameter is required")
        result = _run(lambda: services.get_best_time_suggestion(
            request.user, project, platform,
        ))
        return ok({"suggestion": result})
