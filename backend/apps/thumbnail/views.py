# -*- coding: utf-8 -*-
"""Thumbnail generation API views (Task 36).

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
from .serializers import ThumbnailAssetSerializer, ThumbnailGenerateSerializer


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


class ThumbnailGenerateView(GenericAPIView):
    """POST /api/projects/{id}/thumbnail/generate/ (manage_projects)."""

    serializer_class = ThumbnailAssetSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        body = ThumbnailGenerateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        platform_target = body.validated_data.get("platform_target", "")
        title_text = body.validated_data.get("title_text", "")

        thumb = _run(
            lambda: services.request_thumbnail(
                request.user, project, platform_target, title_text
            )
        )
        return ok({"thumbnail": self.get_serializer(thumb).data})


class ThumbnailListView(GenericAPIView):
    """GET /api/projects/{id}/thumbnail/ (view_projects)."""

    serializer_class = ThumbnailAssetSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        thumbs = services.list_thumbnails(request.user, project)
        return ok({"thumbnails": self.get_serializer(thumbs, many=True).data})


class ThumbnailDetailView(GenericAPIView):
    """GET /api/projects/{id}/thumbnail/<thumbnail_id>/ (view_projects)."""

    serializer_class = ThumbnailAssetSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        thumb = services.get_thumbnail(self.request.user, self.kwargs["thumbnail_id"])
        if not thumb or thumb.project_id != project.id:
            raise NotFound("thumbnail not found")
        return thumb

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        thumb = self.get_object(project)
        return ok({"thumbnail": self.get_serializer(thumb).data})
