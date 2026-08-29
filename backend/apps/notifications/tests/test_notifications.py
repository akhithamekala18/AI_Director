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
