# -*- coding: utf-8 -*-
"""Notification primitive tests (Development Plan Day 9, §20.3.3)."""
from apps.notifications.models import Notification
from apps.notifications.services import notify_approval_request, notify_status


def test_status_event_creates_notification(make_user):
    user = make_user(username="notif_status")
    notification = notify_status(user, "Status changed", "research approved")
    saved = Notification.objects.get(pk=notification.pk)
    assert saved.type == "status"
    assert saved.title == "Status changed"


def test_approval_request_carries_artifact_link(make_user):
    user = make_user(username="notif_approval")
    notification = notify_approval_request(user, "Approval needed", "project", "42", "please review")
    saved = Notification.objects.get(pk=notification.pk)
    assert saved.type == "approval_request"
    assert saved.artifact_type == "project"
    assert saved.artifact_id == "42"


def test_notification_list_is_scoped_to_recipient(api_client, make_user):
    client = api_client(role="Creator", username="notif_owner")
    other = make_user(username="notif_other")
    notify_status(other, "Other's notification")
    notify_status(client.user, "My notification")
    resp = client.get("/api/notifications/")
    assert resp.status_code == 200
    titles = [n["title"] for n in resp.json()["data"]["notifications"]]
    assert "My notification" in titles
    assert "Other's notification" not in titles


def test_notification_mark_read(api_client):
    client = api_client(role="Creator")
    notification = notify_status(client.user, "Read me")
    resp = client.post(f"/api/notifications/{notification.pk}/read/")
    assert resp.status_code == 200
    assert Notification.objects.get(pk=notification.pk).read is True


def test_reminder_notification(make_user):
    from apps.notifications.services import notify_reminder
    user = make_user(username="notif_reminder")
    notification = notify_reminder(user, "Publish soon", "entry", "42", "YouTube upload in 1h")
    saved = Notification.objects.get(pk=notification.pk)
    assert saved.type == "reminder"
    assert saved.artifact_type == "entry"

def test_publish_outcome_notification(make_user):
    from apps.notifications.services import notify_publish_outcome
    user = make_user(username="notif_outcome")
    notification = notify_publish_outcome(user, "Published!", "entry", "99", "YouTube success")
    saved = Notification.objects.get(pk=notification.pk)
    assert saved.type == "publish_outcome"

def test_publish_failure_notification(make_user):
    from apps.notifications.services import notify_publish_failure
    user = make_user(username="notif_failure")
    notification = notify_publish_failure(user, "Upload failed", "entry", "55", "Auth expired")
    saved = Notification.objects.get(pk=notification.pk)
    assert saved.type == "publish_failure"

def test_team_assignment_notification(make_user):
    from apps.notifications.services import notify_team_assignment
    user = make_user(username="notif_team")
    notification = notify_team_assignment(user, "Assigned", "project", "7", "You have been assigned")
    saved = Notification.objects.get(pk=notification.pk)
    assert saved.type == "team_assignment"
