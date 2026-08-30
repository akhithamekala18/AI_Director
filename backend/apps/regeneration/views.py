# -*- coding: utf-8 -*-
"""Regeneration API views (Phase 2G, Task 26).

Follows the Phase 1/2A–2F conventions: token auth, HasCapability authorization,
membership-scoped 404 team isolation (via get_project), and the standard
{success, data} envelope from apps.core.response. The Gate 4 dependency and G-4
scope are enforced server-side in the service layer (never trusted from the
request body).
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
from .serializers import (
    RegenerationRequestCreateSerializer,
    RegenerationRequestSerializer,
)


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


class RegenerationCreateView(GenericAPIView):
    """POST /api/projects/{id}/regenerate/ (manage_projects).

    Enqueues a REGENERATION AsyncJob. Gate 4 approval + G-4 scope are enforced
    server-side (service layer).
    """

    serializer_class = RegenerationRequestCreateSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def post(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        body = RegenerationRequestCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data

        job = _run(
            lambda: services.request_regeneration(
                request.user,
                project,
                scene_id=data.get("scene_id") or None,
                media_types=data.get("media_types") or None,
                full=data.get("full", False),
            )
        )
        return ok(
            {"job": AsyncJobSerializer(job).data, "regeneration": None},
            status=status.HTTP_202_ACCEPTED,
        )


class RegenerationListView(GenericAPIView):
    """GET /api/projects/{id}/regenerate/ (view_projects)."""

    serializer_class = RegenerationRequestSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        reqs = services.list_regeneration_requests(request.user, project)
        return ok({"regeneration": self.get_serializer(reqs, many=True).data})


class RegenerationDetailView(GenericAPIView):
    """GET /api/projects/{id}/regenerate/<request_id>/ (view_projects)."""

    serializer_class = RegenerationRequestSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self, project):
        obj = services.get_regeneration_request(
            self.request.user, self.kwargs["request_id"]
        )
        if not obj or obj.project_id != project.id:
            raise NotFound("regeneration request not found")
        return obj

    def get(self, request, *args, **kwargs):
        project = _get_project(request, self.kwargs["pk"])
        req = self.get_object(project)
        return ok({"regeneration": self.get_serializer(req).data})
