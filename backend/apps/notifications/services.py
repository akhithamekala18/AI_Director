# -*- coding: utf-8 -*-
def notify_status(recipient, title, message=""):
    from apps.core.enums import NotificationType
    from apps.notifications.models import Notification

    return Notification.objects.create(
        recipient=recipient, type=NotificationType.STATUS.value, title=title[:160], message=message[:500]
    )


def notify_approval_request(recipient, title, artifact_type, artifact_id, message=""):
    """Approval-request event carrying the artifact link (Development Plan Day 9)."""
    from apps.core.enums import NotificationType
    from apps.notifications.models import Notification

    return Notification.objects.create(
        recipient=recipient,
        type=NotificationType.APPROVAL_REQUEST.value,
        title=title[:160],
        message=message[:500],
        artifact_type=artifact_type[:64],
        artifact_id=str(artifact_id)[:64],
    )
