# -*- coding: utf-8 -*-
"""Character Library API views (Phase 2D, Task 23).

Follows the Phase 1/2A/2B/2C conventions: token auth, HasCapability
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
from .serializers import CharacterLibrarySerializer, CharacterSerializer


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
    character = services.get_character(user, project)
    if not character:
        raise NotFound("character set not found for this project")
    return character


class CharacterGenerateView(GenericAPIView):
    """POST /api/projects/{id}/character/generate/ (manage_projects)."""

    serializer_class = CharacterSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        character = _run(lambda: services.generate_characters(request.user, project))
        return ok({"character": self.get_serializer(character).data})


class CharacterDetailView(GenericAPIView):
    """GET /api/projects/{id}/character/ (view_projects)."""

    serializer_class = CharacterSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def get(self, request, *args, **kwargs):
        character = self.get_object()
        return ok({"character": self.get_serializer(character).data})


class CharacterApproveView(GenericAPIView):
    """POST /api/projects/{id}/character/approve/ (approve)."""

    serializer_class = CharacterSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        character = _run(
            lambda: services.approve_character(request.user, self.get_object())
        )
        return ok({"character": self.get_serializer(character).data})


class CharacterRequestChangesView(GenericAPIView):
    """POST /api/projects/{id}/character/request-changes/ (approve)."""

    serializer_class = CharacterSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = _get_project(self.request, self.kwargs["pk"])
        return _get_or_404(self.request.user, project)

    def post(self, request, *args, **kwargs):
        reason = request.data.get("reason")
        character = _run(
            lambda: services.request_character_changes(
                request.user, self.get_object(), reason
            )
        )
        return ok({"character": self.get_serializer(character).data})


class CharacterLibraryView(GenericAPIView):
    """GET /api/projects/{id}/character/library/ (view_projects)."""

    serializer_class = CharacterLibrarySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        library = services.list_library(request.user, project)
        return ok({"library": self.get_serializer(library, many=True).data})


class CharacterReuseView(GenericAPIView):
    """POST /api/projects/{id}/character/reuse/ (manage_projects).

    Applies a team library character (by id) to this project, preserving its
    identity (G-5).
    """

    serializer_class = CharacterSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        return _get_project(self.request, self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        library_entry_id = request.data.get("library_entry_id")
        entry = _run(
            lambda: self._get_library_entry(request, library_entry_id)
        )
        character = _run(
            lambda: services.reuse_character(request.user, project, entry)
        )
        return ok({"character": self.get_serializer(character).data})

    def _get_library_entry(self, request, library_entry_id):
        from .models import CharacterLibrary

        if not library_entry_id:
            raise DjangoValidationError("library_entry_id is required")
        team_ids = request.user.memberships.values_list("team_id", flat=True)
        entry = CharacterLibrary.objects.filter(
            id=library_entry_id, team_id__in=team_ids
        ).first()
        if not entry:
            raise DjangoValidationError("library character not found")
        return entry
