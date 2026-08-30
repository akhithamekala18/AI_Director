# -*- coding: utf-8 -*-
"""Research Engine API views (R6, Development Plan Day 21).

Follows the Phase 1/2A conventions: token auth, HasCapability authorization,
membership-scoped 404 team isolation (via get_project), and the standard
{success, data} envelope from apps.core.response.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView

from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects.services import get_project

from . import services
from .serializers import ResearchGapSerializer, ResearchSerializer, ResearchSourceSerializer


def _run(operation):
    """Run a service operation, converting Django ValidationError to a DRF 400."""
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


def _get_or_404(user, project):
    research = services.get_research(user, project)
    if not research:
        raise NotFound("research not found for this project")
    return research


class ResearchGenerateView(GenericAPIView):
    """POST /api/projects/{id}/research/generate/ (manage_projects)."""

    serializer_class = ResearchSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        research = _run(lambda: services.generate_research(request.user, project))
        return ok(
            {"research": _with_counts(research, self.get_serializer(research).data)}
        )


class ResearchDetailView(GenericAPIView):
    """GET /api/projects/{id}/research/ (view_projects)."""

    serializer_class = ResearchSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def get(self, request, *args, **kwargs):
        research = self.get_object()
        self.get_serializer(research)
        return ok(
            {"research": _with_counts(research, self.get_serializer(research).data)}
        )


class ResearchSourcesView(GenericAPIView):
    """GET /api/projects/{id}/research/sources/ (view_projects)."""

    serializer_class = ResearchSourceSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def get(self, request, *args, **kwargs):
        research = self.get_object()
        sources = services.research_sources(request.user, research)
        return ok({"sources": self.get_serializer(sources, many=True).data})


class ResearchApproveView(GenericAPIView):
    """POST /api/projects/{id}/research/approve/ (approve)."""

    serializer_class = ResearchSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        research = _run(lambda: services.approve_research(request.user, self.get_object()))
        return ok({"research": _with_counts(research, self.get_serializer(research).data)})


class ResearchRequestChangesView(GenericAPIView):
    """POST /api/projects/{id}/research/request-changes/ (approve)."""

    serializer_class = ResearchSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        reason = request.data.get("reason")
        research = _run(
            lambda: services.request_research_changes(
                request.user, self.get_object(), reason
            )
        )
        return ok({"research": _with_counts(research, self.get_serializer(research).data)})


class ResearchGapsView(GenericAPIView):
    """GET /api/projects/{id}/research/gaps/ (view_projects)."""

    serializer_class = ResearchGapSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def get(self, request, *args, **kwargs):
        research = self.get_object()
        gaps = services.research_gaps(request.user, research)
        return ok({"gaps": self.get_serializer(gaps, many=True).data})


def _with_counts(research, data):
    """Attach live source/gap counts alongside the serialized research."""
    data = dict(data)
    data["source_count"] = research.sources.count()
    data["gap_count"] = research.gaps.count()
    return data
