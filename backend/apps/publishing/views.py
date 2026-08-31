# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from apps.accounts.permissions import HasCapability
from apps.core.response import ok
from apps.projects.services import get_project
from . import services
from .serializers import (ApproveEntrySerializer, ApprovalSerializer, EntryCreateSerializer, RejectEntrySerializer, ScheduledEntrySerializer, ScheduledPostSerializer, SocialAccountConnectSerializer, SocialAccountSerializer, UploadAttemptSerializer)

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

class SocialAccountListView(GenericAPIView):
    serializer_class = SocialAccountSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        accounts = services.list_social_accounts(request.user)
        return ok({"accounts": self.get_serializer(accounts, many=True).data})

class SocialAccountConnectView(GenericAPIView):
    serializer_class = SocialAccountSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        body = SocialAccountConnectSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        account = _run(lambda: services.connect_social_account(request.user, body.validated_data["platform"], body.validated_data["platform_account_id"], body.validated_data.get("display_name", "")))
        return ok({"account": self.get_serializer(account).data})

class SocialAccountDisconnectView(GenericAPIView):
    serializer_class = SocialAccountSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        account = _run(lambda: services.disconnect_social_account(request.user, kwargs["pk"]))
        return ok({"account": self.get_serializer(account).data})

class PostCreateView(GenericAPIView):
    serializer_class = ScheduledPostSerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        project = _get_project(request, kwargs["pk"])
        video_id = request.data.get("video_id")
        video = None
        if video_id:
            from apps.video.models import VideoAsset
            video = VideoAsset.objects.filter(id=video_id, project=project).first()
            if not video:
                raise NotFound("video not found")
        post = _run(lambda: services.create_post(request.user, project, video))
        return ok({"post": self.get_serializer(post).data})

class PostListView(GenericAPIView):
    serializer_class = ScheduledPostSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        project = _get_project(request, kwargs["pk"])
        posts = services.list_posts(request.user, project)
        return ok({"posts": self.get_serializer(posts, many=True).data})

class PostDetailView(GenericAPIView):
    serializer_class = ScheduledPostSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        post = services.get_post(request.user, kwargs["post_id"])
        if not post or post.project_id != int(kwargs["pk"]):
            raise NotFound("post not found")
        return ok({"post": self.get_serializer(post).data})

class EntryCreateView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        post_id = request.data.get("post_id")
        if not post_id:
            raise ValidationError("post_id is required")
        post = services.get_post(request.user, post_id)
        if not post:
            raise NotFound("post not found")
        body = EntryCreateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry = _run(lambda: services.create_entry(request.user, post, body.validated_data["social_account_id"], body.validated_data["scheduled_utc"], body.validated_data.get("timezone", "UTC")))
        return ok({"entry": self.get_serializer(entry).data})

class EntryListView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        post_id = request.query_params.get("post_id")
        if not post_id:
            raise ValidationError("post_id query parameter is required")
        post = services.get_post(request.user, post_id)
        if not post:
            raise NotFound("post not found")
        entries = services.list_entries(request.user, post)
        return ok({"entries": self.get_serializer(entries, many=True).data})

class EntryCancelView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        entry = _run(lambda: services.cancel_entry(request.user, entry))
        return ok({"entry": self.get_serializer(entry).data})

class ApprovalView(GenericAPIView):
    serializer_class = ApprovalSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        body = ApproveEntrySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        approval = _run(lambda: services.approve_entry(request.user, entry, body.validated_data.get("reason", "")))
        return ok({"approval": self.get_serializer(approval).data})

class RejectionView(GenericAPIView):
    serializer_class = ApprovalSerializer
    permission_classes = [HasCapability]
    capability = "approve"
    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        body = RejectEntrySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        approval = _run(lambda: services.reject_entry(request.user, entry, body.validated_data.get("reason", "")))
        return ok({"approval": self.get_serializer(approval).data})

class ApprovalListView(GenericAPIView):
    serializer_class = ApprovalSerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        approvals = services.list_approvals(request.user, entry)
        return ok({"approvals": self.get_serializer(approvals, many=True).data})

class UploadView(GenericAPIView):
    serializer_class = UploadAttemptSerializer
    permission_classes = [HasCapability]
    capability = "publish"
    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        attempt = _run(lambda: services.create_upload_attempt(request.user, entry))
        return ok({"attempt": self.get_serializer(attempt).data})

class PublishingHistoryView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        project = _get_project(request, kwargs["pk"])
        entries = services.get_publishing_history(request.user, project)
        return ok({"history": self.get_serializer(entries, many=True).data})

class PendingApprovalsView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "view_projects"
    def get(self, request, *args, **kwargs):
        entries = services.get_pending_approvals(request.user)
        return ok({"pending": self.get_serializer(entries, many=True).data})


class RescheduleEntryView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        new_utc = request.data.get("scheduled_utc")
        new_tz = request.data.get("timezone")
        if not new_utc:
            raise ValidationError("scheduled_utc is required")
        entry, invalidated = _run(lambda: services.reschedule_entry(request.user, entry, new_utc, new_tz))
        return ok({"entry": self.get_serializer(entry).data, "invalidated_approvals": invalidated})


class ChangePlatformView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        new_platform = request.data.get("platform")
        new_sa_id = request.data.get("social_account_id")
        if not new_platform:
            raise ValidationError("platform is required")
        entry, invalidated = _run(lambda: services.change_entry_platform(request.user, entry, new_platform, new_sa_id))
        return ok({"entry": self.get_serializer(entry).data, "invalidated_approvals": invalidated})


class RecheckApprovalsView(GenericAPIView):
    permission_classes = [HasCapability]
    capability = "manage_projects"
    def post(self, request, *args, **kwargs):
        expired = services.recheck_expired_approvals(request.user)
        return ok({"expired_count": expired})
class RetryEntryView(GenericAPIView):
    serializer_class = ScheduledEntrySerializer
    permission_classes = [HasCapability]
    capability = "manage_projects"

    def post(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        attempt = _run(lambda: services.trigger_retry(request.user, entry))
        return ok({"attempt": UploadAttemptSerializer(attempt).data})


class RetryStatusView(GenericAPIView):
    permission_classes = [HasCapability]
    capability = "view_projects"

    def get(self, request, *args, **kwargs):
        entry = services.get_entry(request.user, kwargs["entry_id"])
        if not entry:
            raise NotFound("entry not found")
        status = services.get_retry_status(entry)
        return ok({"retry_status": status})