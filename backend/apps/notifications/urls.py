# -*- coding: utf-8 -*-
from django.urls import path

from apps.notifications.views import NotificationListView, NotificationReadView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
]
