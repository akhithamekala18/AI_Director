# -*- coding: utf-8 -*-
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from apps.core.response import ok
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(GenericAPIView):
    """Notifications center shell: status + approval-request (Day 17)."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = Notification.objects.filter(recipient=request.user)[:100]
        return ok({"notifications": self.get_serializer(qs, many=True).data})


class NotificationReadView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        notification = Notification.objects.filter(id=pk, recipient=request.user).first()
        if not notification:
            raise NotFound("notification not found")
        notification.read = True
        notification.save(update_fields=["read"])
        return ok({"notification": NotificationSerializer(notification).data})
