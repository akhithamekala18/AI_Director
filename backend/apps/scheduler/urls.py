# -*- coding: utf-8 -*-
from django.urls import path

from .views import (
    ScheduleBestTimeView,
    ScheduleCalendarView,
    ScheduleCancelView,
    ScheduleCreateView,
    ScheduleDetailView,
    ScheduleListView,
    ScheduleRescheduleView,
)

urlpatterns = [
    path("", ScheduleListView.as_view(), name="schedule-list"),
    path("create/", ScheduleCreateView.as_view(), name="schedule-create"),
    path("calendar/", ScheduleCalendarView.as_view(), name="schedule-calendar"),
    path("best-time/", ScheduleBestTimeView.as_view(), name="schedule-best-time"),
    path("<int:entry_id>/", ScheduleDetailView.as_view(), name="schedule-detail"),
    path(
        "<int:entry_id>/reschedule/",
        ScheduleRescheduleView.as_view(),
        name="schedule-reschedule",
    ),
    path(
        "<int:entry_id>/cancel/",
        ScheduleCancelView.as_view(),
        name="schedule-cancel",
    ),
]
