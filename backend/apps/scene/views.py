# -*- coding: utf-8 -*-
"""Scene Builder API views (Phase 2E, Task 24).

Follows the Phase 1/2A/2B/2C/2D conventions: token auth, HasCapability
authorization, membership-scoped 404 team isolation (via get_project), and the
standard {success, data} envelope from apps.core.response.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView

from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects.services import get_project

from . import services
from .serializers import SceneBuilderSerializer


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
    builder = services.get_scene_builder(user, project)
    if not builder:
        raise NotFound("scene package not found for this project")
    return builder


class SceneBuildView(GenericAPIView):
    """POST /api/projects/{id}/scene/build/ (manage_projects)."""

    serializer_class = SceneBuilderSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        builder = _run(lambda: services.build_scenes(request.user, project))
        return ok({"scene": self.get_serializer(builder).data})


class SceneDetailView(GenericAPIView):
    """GET /api/projects/{id}/scene/ (view_projects)."""

    serializer_class = SceneBuilderSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def get(self, request, *args, **kwargs):
        builder = self.get_object()
        return ok({"scene": self.get_serializer(builder).data})


class SceneApproveView(GenericAPIView):
    """POST /api/projects/{id}/scene/approve/ (approve)."""

    serializer_class = SceneBuilderSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        builder = _run(
            lambda: services.approve_scene_builder(request.user, self.get_object())
        )
        return ok({"scene": self.get_serializer(builder).data})


class SceneRequestChangesView(GenericAPIView):
    """POST /api/projects/{id}/scene/request-changes/ (approve)."""

    serializer_class = SceneBuilderSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        reason = request.data.get("reason")
        builder = _run(
            lambda: services.request_scene_changes(
                request.user, self.get_object(), reason
            )
        )
        return ok({"scene": self.get_serializer(builder).data})
