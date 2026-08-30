# -*- coding: utf-8 -*-
"""Scene media API views (Phase 2F, Task 25).

Follows the Phase 1/2A–2E conventions: token auth, HasCapability authorization,
membership-scoped 404 team isolation (via get_project), and the standard
{success, data} envelope from apps.core.response. The Gate 4 dependency is
enforced server-side in the service layer (never trusted from the request body).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView

from apps.accounts.permissions import HasCapability
from apps.ai_orchestration.serializers import AsyncJobSerializer
from apps.core.response import ok
from apps.projects.services import get_project

from . import services
from .serializers import SceneMediaGenerateSerializer, SceneMediaSerializer


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


class SceneMediaGenerateView(GenericAPIView):
    """POST /api/projects/{id}/scene-media/generate/ (manage_projects).

    Requires Gate 4 approval server-side (service layer). Enqueues a
    SCENE_MEDIA_GENERATION AsyncJob and returns it.
    """

    serializer_class = SceneMediaGenerateSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def post(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        body = SceneMediaGenerateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        media_types = body.validated_data.get("media_types") or None

        job = _run(
            lambda: services.request_scene_media(
                request.user, project, media_types=media_types
            )
        )
        return ok(
            {"job": AsyncJobSerializer(job).data}, status=status.HTTP_202_ACCEPTED
        )


class SceneMediaListView(GenericAPIView):
    """GET /api/projects/{id}/scene-media/ (view_projects)."""

    serializer_class = SceneMediaSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        media = services.list_scene_media(request.user, project)
        return ok({"media": self.get_serializer(media, many=True).data})


class SceneMediaDetailView(GenericAPIView):
    """GET /api/projects/{id}/scene-media/<media_id>/ (view_projects)."""

    serializer_class = SceneMediaSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        obj = services.get_scene_media(self.request.user, self.kwargs["media_id"])
        if not obj or obj.project_id != project.id:
            raise NotFound("scene media not found")
        return obj

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        media = self.get_object(project)
        return ok({"media": self.get_serializer(media).data})
