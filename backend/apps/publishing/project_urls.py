# -*- coding: utf-8 -*-
from django.urls import path
from .views import (PostCreateView, PostListView, PostDetailView, EntryCreateView, EntryListView, EntryCancelView, ApprovalView, RejectionView, ApprovalListView, UploadView, PublishingHistoryView, RescheduleEntryView, ChangePlatformView)

urlpatterns = [
    path("posts/", PostListView.as_view(), name="post-list"),
    path("posts/create/", PostCreateView.as_view(), name="post-create"),
    path("posts/<int:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path("entries/create/", EntryCreateView.as_view(), name="entry-create"),
    path("entries/", EntryListView.as_view(), name="entry-list"),
    path("entries/<int:entry_id>/cancel/", EntryCancelView.as_view(), name="entry-cancel"),
    path("entries/<int:entry_id>/approve/", ApprovalView.as_view(), name="entry-approve"),
    path("entries/<int:entry_id>/reject/", RejectionView.as_view(), name="entry-reject"),
    path("entries/<int:entry_id>/approvals/", ApprovalListView.as_view(), name="approval-list"),
    path("entries/<int:entry_id>/upload/", UploadView.as_view(), name="entry-upload"),
    path("history/", PublishingHistoryView.as_view(), name="publishing-history"),
    path("entries/<int:entry_id>/reschedule/", RescheduleEntryView.as_view(), name="entry-reschedule"),
    path("entries/<int:entry_id>/change-platform/", ChangePlatformView.as_view(), name="entry-change-platform"),
]
