# -*- coding: utf-8 -*-
"""Preview API views (Task 37).

Follows the Phase 2F conventions: token auth, HasCapability authorization,
membership-scoped 404 team isolation, and the standard {success, data}
envelope from apps.core.response.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView

from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects.services import get_project

from . import services
from .serializers import (
    PreviewAssetSerializer,
    PreviewApproveSerializer,
    PreviewGenerateSerializer,
    PreviewRejectSerializer,
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


class PreviewGenerateView(GenericAPIView):
    """POST /api/projects/{id}/preview/generate/ (manage_projects)."""

    serializer_class = PreviewAssetSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        body = PreviewGenerateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        platform_target = body.validated_data.get("platform_target", "YouTube")

        preview = _run(
            lambda: services.request_preview(request.user, project, platform_target)
        )
        return ok({"preview": self.get_serializer(preview).data})


class PreviewListView(GenericAPIView):
    """GET /api/projects/{id}/preview/ (view_projects)."""

    serializer_class = PreviewAssetSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        previews = services.list_previews(request.user, project)
        return ok({"previews": self.get_serializer(previews, many=True).data})


class PreviewDetailView(GenericAPIView):
    """GET /api/projects/{id}/preview/<preview_id>/ (view_projects)."""

    serializer_class = PreviewAssetSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        preview = services.get_preview(self.request.user, self.kwargs["preview_id"])
        if not preview or preview.project_id != project.id:
            raise NotFound("preview not found")
        return preview

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        preview = self.get_object(project)
        return ok({"preview": self.get_serializer(preview).data})


class PreviewApproveView(GenericAPIView):
    """POST /api/projects/{id}/preview/<preview_id>/approve/ (manage_projects)."""

    serializer_class = PreviewAssetSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        preview = services.get_preview(self.request.user, self.kwargs["preview_id"])
        if not preview or preview.project_id != project.id:
            raise NotFound("preview not found")
        return preview

    def post(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        preview = self.get_object(project)
        body = PreviewApproveSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        preview = _run(lambda: services.approve_preview(request.user, preview))
        return ok({"preview": self.get_serializer(preview).data})


class PreviewRejectView(GenericAPIView):
    """POST /api/projects/{id}/preview/<preview_id>/reject/ (manage_projects)."""

    serializer_class = PreviewAssetSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        preview = services.get_preview(self.request.user, self.kwargs["preview_id"])
        if not preview or preview.project_id != project.id:
            raise NotFound("preview not found")
        return preview

    def post(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        preview = self.get_object(project)
        body = PreviewRejectSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        reason = body.validated_data.get("reason", "")

        preview = _run(lambda: services.reject_preview(request.user, preview, reason))
        return ok({"preview": self.get_serializer(preview).data})
