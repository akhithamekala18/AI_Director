# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects import services
from apps.projects.serializers import ProjectSerializer, ProjectTransitionSerializer


def _run(operation):
    """Run a service operation, converting Django ValidationError to a DRF 400."""
    try:
        result = operation()
    except DjangoValidationError as exc:
        messages = getattr(exc, "messages", None) or [str(exc)]
        raise ValidationError(" ".join(messages)) from exc
    return result


class ProjectListCreateView(GenericAPIView):
    """List (team-scoped) and create projects (Day 6, Day 13/14)."""

    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            self.capability = "manage_projects"
            return [HasCapability()]
        return [IsAuthenticated()]

    def get(self, request, *args, **kwargs):
        include_archived = request.query_params.get("archived", "0") == "1"
        qs = services.list_projects_for(request.user, include_archived=include_archived)
        return ok({"projects": self.get_serializer(qs, many=True).data})

    def post(self, request, *args, **kwargs):
        validate_topic(request.data)
        project = _run(
            lambda: services.create_project(
                request.user,
                request.data.get("topic", ""),
                platform_target=request.data.get("platform_target", ""),
                format_name=request.data.get("format", ""),
                is_template=bool(request.data.get("is_template", False)),
            )
        )
        return ok({"project": self.get_serializer(project).data}, status=status.HTTP_201_CREATED)


def validate_topic(data):
    topic = (data.get("topic") or "").strip()
    if not topic:
        raise ValidationError("topic is required")


class ProjectDetailView(GenericAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = services.get_project(self.request.user, self.kwargs["pk"])
        if not project:
            raise NotFound("project not found")
        return project

    def get(self, request, *args, **kwargs):
        return ok({"project": self.get_serializer(self.get_object()).data})

    def patch(self, request, *args, **kwargs):
        project = _run(
            lambda: services.update_metadata(request.user, self.get_object(), {
                "topic": request.data.get("topic"),
                "platform_target": request.data.get("platform_target"),
                "format": request.data.get("format"),
            })
        )
        return ok({"project": self.get_serializer(project).data})


class ProjectArchiveView(GenericAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = services.get_project(self.request.user, self.kwargs["pk"])
        if not project:
            raise NotFound("project not found")
        return project

    def post(self, request, *args, **kwargs):
        project = _run(lambda: services.archive_project(request.user, self.get_object()))
        return ok({"project": self.get_serializer(project).data})


class ProjectDuplicateView(GenericAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = services.get_project(self.request.user, self.kwargs["pk"])
        if not project:
            raise NotFound("project not found")
        return project

    def post(self, request, *args, **kwargs):
        copy = _run(lambda: services.duplicate_project(request.user, self.get_object()))
        return ok({"project": self.get_serializer(copy).data}, status=status.HTTP_201_CREATED)


class ProjectTemplateCreateView(GenericAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        template = services.get_project(self.request.user, self.kwargs["pk"])
        if not template or not template.is_template:
            raise NotFound("template not found")
        return template

    def post(self, request, *args, **kwargs):
        copy = _run(lambda: services.create_from_template(request.user, self.get_object()))
        return ok({"project": self.get_serializer(copy).data}, status=status.HTTP_201_CREATED)


class ProjectTransitionView(GenericAPIView):
    serializer_class = ProjectTransitionSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        project = services.get_project(self.request.user, self.kwargs["pk"])
        if not project:
            raise NotFound("project not found")
        return project

    def post(self, request, *args, **kwargs):
        transition_serializer = ProjectTransitionSerializer(data=request.data)
        transition_serializer.is_valid(raise_exception=True)
        target = transition_serializer.validated_data["target_state"]
        project = _run(lambda: services.transition(request.user, self.get_object(), target))
        return ok({"project": ProjectSerializer(project).data})
