# -*- coding: utf-8 -*-
"""DRF views for AI orchestration endpoints."""
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects.services import get_project

from .models import AsyncJob
from .serializers import AsyncJobSerializer, CreateJobSerializer
from .services import cancel_job, create_job, get_job, list_jobs_for_project, retry_job


class JobListCreateView(GenericAPIView):
    """List and create async jobs."""

    serializer_class = AsyncJobSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            self.capability = "manage_projects"
            return [HasCapability()]
        return [IsAuthenticated()]

    def get(self, request, *args, **kwargs):
        project_id = request.query_params.get("project_id")
        if not project_id:
            return ok({"jobs": []})

        project = get_project(request.user, project_id)
        if not project:
            raise NotFound("project not found")

        jobs = list_jobs_for_project(request.user, project)
        return ok({"jobs": self.get_serializer(jobs, many=True).data})

    def post(self, request, *args, **kwargs):
        serializer = CreateJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = get_project(request.user, serializer.validated_data["project_id"])
        if not project:
            raise NotFound("project not found")

        job = create_job(
            user=request.user,
            project=project,
            job_type=serializer.validated_data["job_type"],
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return ok(
            {"job": AsyncJobSerializer(job).data},
            status=status.HTTP_201_CREATED,
        )


class JobDetailView(GenericAPIView):
    """Get job details."""

    serializer_class = AsyncJobSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "pk"

    def get_object(self):
        job = get_job(self.request.user, self.kwargs["pk"])
        if not job:
            raise NotFound("job not found")
        return job

    def get(self, request, *args, **kwargs):
        return ok({"job": self.get_serializer(self.get_object()).data})


class JobCancelView(GenericAPIView):
    """Cancel a job."""

    serializer_class = AsyncJobSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        job = get_job(self.request.user, self.kwargs["pk"])
        if not job:
            raise NotFound("job not found")
        return job

    def post(self, request, *args, **kwargs):
        job = self.get_object()
        try:
            cancel_job(request.user, job)
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc))
        return ok({"job": AsyncJobSerializer(job).data})


class JobRetryView(GenericAPIView):
    """Retry a failed job."""

    serializer_class = AsyncJobSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    lookup_url_kwarg = "pk"

    def get_object(self):
        job = get_job(self.request.user, self.kwargs["pk"])
        if not job:
            raise NotFound("job not found")
        return job

    def post(self, request, *args, **kwargs):
        job = self.get_object()
        try:
            retry_job(request.user, job)
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(exc))
        return ok({"job": AsyncJobSerializer(job).data})
