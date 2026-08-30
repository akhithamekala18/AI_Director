# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/projects/", include("apps.projects.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/settings/", include("apps.settings_app.urls")),
    path("api/core/", include("apps.core.urls")),
    path("api/orchestration/", include("apps.ai_orchestration.urls")),
    path("api/projects/<int:pk>/research/", include("apps.research.urls")),
]
