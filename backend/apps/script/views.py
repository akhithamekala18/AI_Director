# -*- coding: utf-8 -*-
"""Script Engine API views (R6, Development Plan Day 22).

Follows the Phase 1/2A/2B conventions: token auth, HasCapability authorization,
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
from .serializers import ScriptSerializer


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
    script = services.get_script(user, project)
    if not script:
        raise NotFound("script not found for this project")
    return script


class ScriptGenerateView(GenericAPIView):
    """POST /api/projects/{id}/script/generate/ (manage_projects)."""

    serializer_class = ScriptSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        script = _run(lambda: services.generate_script(request.user, project))
        return ok({"script": self.get_serializer(script).data})


class ScriptDetailView(GenericAPIView):
    """GET /api/projects/{id}/script/ (view_projects)."""

    serializer_class = ScriptSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def get(self, request, *args, **kwargs):
        script = self.get_object()
        return ok({"script": self.get_serializer(script).data})


class ScriptApproveView(GenericAPIView):
    """POST /api/projects/{id}/script/approve/ (approve)."""

    serializer_class = ScriptSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        script = _run(
            lambda: services.approve_script(request.user, self.get_object())
        )
        return ok({"script": self.get_serializer(script).data})


class ScriptRequestChangesView(GenericAPIView):
    """POST /api/projects/{id}/script/request-changes/ (approve)."""

    serializer_class = ScriptSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        reason = request.data.get("reason")
        script = _run(
            lambda: services.request_script_changes(
                request.user, self.get_object(), reason
            )
        )
        return ok({"script": self.get_serializer(script).data})
