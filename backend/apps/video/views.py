# -*- coding: utf-8 -*-
"""Video generation API views (Task 36).

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
from .serializers import VideoAssetSerializer, VideoGenerateSerializer


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


class VideoGenerateView(GenericAPIView):
    """POST /api/projects/{id}/video/generate/ (manage_projects)."""

    serializer_class = VideoAssetSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        body = VideoGenerateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        platform_target = body.validated_data.get("platform_target", "")

        video = _run(
            lambda: services.request_video(request.user, project, platform_target)
        )
        return ok({"video": self.get_serializer(video).data})


class VideoListView(GenericAPIView):
    """GET /api/projects/{id}/video/ (view_projects)."""

    serializer_class = VideoAssetSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        videos = services.list_videos(request.user, project)
        return ok({"videos": self.get_serializer(videos, many=True).data})


class VideoDetailView(GenericAPIView):
    """GET /api/projects/{id}/video/<video_id>/ (view_projects)."""

    serializer_class = VideoAssetSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        video = services.get_video(self.request.user, self.kwargs["video_id"])
        if not video or video.project_id != project.id:
            raise NotFound("video not found")
        return video

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        video = self.get_object(project)
        return ok({"video": self.get_serializer(video).data})
